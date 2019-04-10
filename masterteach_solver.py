#!/usr/bin/python
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import math
import roslib
import rospy
import time

# ret_codeとmessage送信時にsleepを使う
from time import sleep 

# yamlファイルからrosparamへの書き込み用
from rosparam import upload_params

#パラメータ登録・取得・削除用(yamlファイルに保存している)
import yaml
from yaml import load # yamlファイルからrosparamへの書き込み用

#デバッグファイル名作成用
import datetime

#readPLY用
import open3d as o3d

#マスターRTをオブジェクトとして保存する
import pickle
import os.path
import shutil
import glob

from rovi.msg import Floats

from rospy.numpy_msg import numpy_msg
from std_msgs.msg import Bool
from std_msgs.msg import String
from std_srvs.srv import Trigger,TriggerRequest
from sensor_msgs.msg import PointCloud
from sensor_msgs.msg import ChannelFloat32
from geometry_msgs.msg import Point32
from geometry_msgs.msg import Point
from geometry_msgs.msg import Transform
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), os.environ['ROVI_PATH'] + '/script'))
import tflib
import tf

from collections import deque

from jsk_rviz_plugins.msg import OverlayText

#マスター点群（クロップ済みのロボット座標点群）ファイル名
master_ply_file_name_base = 'master'

#マスター位置(RT)ファイル名 ※bTm
master_rt_file_name_base = 'master_bTm'

#マスターパラメータ（一致率閾値、露光時間、ゲインが設定される）ファイル名
master_param_file_name_base = 'master_param'

#バックアップパラメータ（/rovi配下のパラメータ）ファイル名
rovi_param_file_name_base = 'rovi_param'

#オリジナルのキャリブパラメータファイルパス
rcalib_yaml_path = os.environ['HOME'] + '/.ros/rcalib.yaml'

#バックアップキャリブパラメータ(HOME/.ros/rcalib.param）ファイル名
rcalib_param_file_name_base = 'rcalib'

#roviから取得するパラメータ
rovi_exposure_time_field_path = '/rovi/pshift_genpc/camera/ExposureTime'
rovi_gain_field_path = '/rovi/pshift_genpc/camera/Gain'
rovi_projector_exposure_time_field_path = '/rovi/pshift_genpc/projector/ExposureTime'
rovi_projector_intencity_field_path = '/rovi/pshift_genpc/projector/Intencity'
rovi_projector_interval_field_path = '/rovi/pshift_genpc/projector/Interval'

def xyz2quat(e):
  tf=Transform()
  k = math.pi / 180 * 0.5
  cx = math.cos(e.rotation.x * k)
  cy = math.cos(e.rotation.y * k)
  cz = math.cos(e.rotation.z * k)
  sx = math.sin(e.rotation.x * k)
  sy = math.sin(e.rotation.y * k)
  sz = math.sin(e.rotation.z * k)
  tf.translation.x=e.translation.x
  tf.translation.y=e.translation.y
  tf.translation.z=e.translation.z
  tf.rotation.x = cy * cz * sx - cx * sy * sz
  tf.rotation.y = cy * sx * sz + cx * cz * sy
  tf.rotation.z = cx * cy * sz - cz * sx * sy
  tf.rotation.w = sx * sy * sz + cx * cy * cz
  return tf

def check_obst(e):
  global scnPn
  q=xyz2quat(e)
#  print 'base2work quat',e
  i=np.linalg.inv(tflib.toRT(q))
#  print 'base2work inv rt',i
  P=np.vstack((scnPn.T,np.ones((1,len(scnPn)))))
  tp=np.dot(i[:3],P).T
#  print "work2base points",tp.shape,tp
  W=np.where(tp.T[0]>=-6.0)
  tp=tp[W[len(W)-1]]
  W=np.where(tp.T[0]<=+6.0)
  tp=tp[W[len(W)-1]]
  W=np.where(tp.T[1]>=-6.0)
  tp=tp[W[len(W)-1]]
  W=np.where(tp.T[1]<=+6.0)
  tp=tp[W[len(W)-1]]
  W=np.where(tp.T[2]>=+8.0)
  tp=tp[W[len(W)-1]]
  W=np.where(tp.T[2]<=+50.0)
  tp=tp[W[len(W)-1]]
#  d=tp.astype(np.float32)
#  cv2.ppf_match_3d.writePLY(d,'obs.ply')
  print "tp",len(tp),tp.shape
  return True if (len(tp)<100) else False

def robot_rxyzabc_to_rt(rx, ry, rz, a_rad, b_rad, c_rad):
  matrix44 = np.zeros((4, 4))
  x_mat = np.zeros((4, 4))
  y_mat = np.zeros((4, 4))
  z_mat = np.zeros((4, 4))

  matrix44[3, 3] = 1
  matrix44[0, 3] = rx
  matrix44[1, 3] = ry
  matrix44[2, 3] = rz

  x_mat[0, 0] = 1.0
  x_mat[1, 1] = np.cos(a_rad)
  x_mat[1, 2] = -np.sin(a_rad)
  x_mat[2, 1] = np.sin(a_rad)
  x_mat[2, 2] = np.cos(a_rad)

  y_mat[0, 0] = np.cos(a_rad)
  y_mat[0, 2] = np.sin(b_rad)
  y_mat[1, 1] = 1.0
  y_mat[2, 0] = -np.sin(b_rad)
  y_mat[2, 2] = np.cos(b_rad)

  z_mat[0, 0] = np.cos(c_rad)
  z_mat[0, 1] = -np.sin(c_rad)
  z_mat[1, 0] = np.sin(c_rad)

  z_mat[1, 1] = np.cos(c_rad)
  z_mat[2, 2] = 1.0

  temp_mat1 = np.zeros((3, 3))
  temp_mat2 = np.zeros((3, 3))

  for m in range(3):
    for n in range(3):
      for k in range(3):
        temp_mat1[m, n] += y_mat[m, k] * z_mat[k, n]

  for m in range(3):
    for n in range(3):
      for k in range(3):
        temp_mat2[m, n] += x_mat[m, k] * temp_mat1[k, n]

  for m in range(3):
    for n in range(3):
      matrix44[m, n] = temp_mat2[m, n]

  return matrix44

def P0():
  return np.array([]).reshape((-1,3))

def np2Fm(d):  #numpy to Floats (unit is meter for RViZ)
  f=Floats()
  f.data=np.ravel(d) / 1000.0
  return f

def np2FmNoDivide(d):  #numpy to Floats (unit is already meter for RViZ)
  f=Floats()
  f.data=np.ravel(d)
  return f

def np2F(d):  #numpy to Floats
  f=Floats()
  f.data=np.ravel(d)
  return f

def pc2arr(pc):
  return np.asarray(pc.points)

##########################################
# getRecipeIdFromRosParam
# rosparamからレシピIDを取得する
##########################################
def getRecipeIdFromRosParam():
  global recipe_id

  # パラメータ取得
  # レシピID
  recipe_id = str(rospy.get_param('/mt/recipe',None))
  if(recipe_id == None): # recipe_idが無い場合はエラー
    print '### recipe_id is None' 
    recipe_id = ''
    return False
  else:
    if(len(recipe_id) == 0):
      print '### recipe_id len=zero' 
      recipe_id = ''
      return False

  print '###### recipe_id=', recipe_id
  return True

##########################################
# makeMasterFilePath
# レシピIDに該当するマスターファイルのパスを作成する
##########################################
def makeMasterFilePath(recipe_id):
    global master_ply, master_rt, master_param, rovi_param, rcalib_param

    master_ply = master_dir + master_ply_file_name_base + '_' + str(recipe_id) + '.ply'		#マスター点群（クロップ済みのロボット座標点群）ファイルパス
    master_rt = master_dir + master_rt_file_name_base + '_' + str(recipe_id) + '_rt'		#マスター位置(RT)ファイルパス(bTmを保存している)
    master_param = master_dir + master_param_file_name_base + '_' + str(recipe_id) + '.yaml'	#マスターパラメータファイルパス(fitness_threshold,exposure_time,gainを保存している)
    rovi_param = master_dir + rovi_param_file_name_base + '_' + str(recipe_id) + '.yaml'	#バックアップパラメータファイルパス(/rovi配下を保存している) 
    rcalib_param = master_dir + rcalib_param_file_name_base + '_' + str(recipe_id) + '.yaml'	#rcalib.yamlファイルパス 

    print "master_ply:"+master_ply
    print "master_rt:"+master_rt
    print "master_param:"+master_param
    print "rovi_param:"+rovi_param
    print "rcalib_param:"+rcalib_param

    return

##########################################
# getConfigParamFloatFromDict
# dict(config)から、指定されたkeyのパラメータ値を取得し、floatで返す
# 存在しない場合はdefault_valueを返す
##########################################
def getConfigParamFloatFromDict(config,master_tag,key,default_value):
      ret = default_value
      if(key in config[master_tag]):
        ret = float(config[master_tag][key])
        print '###### ' + key + ' is exist val=' + str(ret)
      else:
        print '###### ' + key + ' is not exist val=' + str(ret)
  
      return ret

##########################################
# getConfigParamIntFromDict
# dict(config)から、指定されたkeyのパラメータ値を取得し、intで返す
# 存在しない場合はdefault_valueを返す
##########################################
def getConfigParamIntFromDict(config,master_tag,key,default_value):
      ret = default_value
      if(key in config[master_tag]):
        ret = int(config[master_tag][key])
        print '###### ' + key + ' is exist val=' + str(ret)
      else:
        print '###### ' + key + ' is not exist val=' + str(ret)
  
      return ret

##########################################
# 点群ファイル読み込み 
##########################################
def readPLY(path):
  if( not os.path.exists(path)): return P0()
  #if not fileExists(path): return P0()
  pc=o3d.PointCloud()
  pc=o3d.read_point_cloud(path)
  return pc2arr(pc)

##########################################
# マスター登録チェック　True:登録済み False:未登録
##########################################
def isMasterRegisterd():
  global master_ply, master_param, master_rt, rovi_param, rcalig_param

  # マスターplyファイルが存在しなければFalse
  if(not os.path.exists(master_ply)):
    print 'isMasterRegisterd: master_ply not found'
    return False

  # マスターパラメータファイルが存在しなければFalse
  if(not os.path.exists(master_param)):
    print 'isMasterRegisterd: master_param not found'
    return False

  # マスターRTファイルが存在しなければFalse
  if(not os.path.exists(master_rt)):
    print 'isMasterRegisterd: master_rt not found'
    return False

  #バックアップパラメータファイル削除
  if(not os.path.exists(rovi_param)):
    print 'isMasterRegisterd: rovi_param not found'
    return False

  #rcalibパラメータファイル削除
  if(not os.path.exists(rcalib_param)):
    print 'isMasterRegisterd: rcalib_param not found'
    return False

  return True

##########################################
# キャプチャー
##########################################
def capture_scene(f):
  print "##### start capture_scene " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")

  global bTm, bTmLat, fromUI

  bTmLat=np.copy(bTm)
  print "bTm latched",bTmLat
  genpc=None
  try:
    genpc=rospy.ServiceProxy('/rovi/pshift_genpc',Trigger)
    req=TriggerRequest()
    ret=genpc(req)      #will continue to callback cb_ps
    print "genpc result: ",ret
    if (ret.success==False):
      publish_retCode_and_message(str(101),str("CAPTURE:genpc failed"))
      if(fromUI == False):
        pub_Y1.publish(False)
      return
  except rospy.ServiceException, e:
    print 'Genpc proxy failed:',e
    publish_retCode_and_message(str(102),str("CAPTURE:genpc proxy failed"))
    if(fromUI == False):
      pub_Y1.publish(False)
    return

  return

##########################################
# RECIPE
# icpを行う対象を指定する。
##########################################
def recipe(f):
  global recipe_id, master_ply, master_param, master_rt, fromUI

  # パラメータ取得
  # レシピID
  if(getRecipeIdFromRosParam() == False): # recipe_idが無い場合はエラー
    publish_retCode_and_message(str(201),str("RECIPE:recipe_id not registerd"))
    if(fromUI == False):
      pub_Y3.publish(False)
    return

  try:
    print "cb_recipe:change recipe_id=" , recipe_id

    # recipe_idに該当するマスターファイルのパスを作成
    makeMasterFilePath(recipe_id)

    # マスターが未登録の場合はエラー
    if(isMasterRegisterd() == False):
      print 'ERROR: db_recipe master not registerd'
      publish_retCode_and_message(str(202),str("RECIPE:master not registerd"))
      if(fromUI == False):
        pub_Y3.publish(False)
      return
    
    # マスターパラメータ（fitness_threshold,exposure_time,gainを保存している)ファイルをrosparamに設定
    f = open(master_param, 'r')
    yamlfile = load(f)
    f.close()
    upload_params('/', yamlfile)

    # マスターのロボット座標(1枚目撮影位置)を通知
    try:
      with open(master_rt, 'rb') as f:
        master_bTm = pickle.load(f)
    except Exception as e:
      print "master_btm_rt file read exception: ", e
      publish_retCode_and_message(str(203),str("RECIPE:master_btm_rt file read exception"))
      if(fromUI == False):
        pub_Y3.publish(False)
      return
    
    pub_model_tf.publish(tflib.fromRT(master_bTm))

    # cropperパラメータをrosparamに設定およびalgorの通知
    if rospy.has_param('/mt/master'):
      cropper_param = rospy.get_param('/mt/master/cropper')
      upload_params('/cropper', cropper_param)

      # algorを通知
      master_algor = rospy.get_param('/mt/master/algor',1)
      pub_model_algor.publish(str(master_algor))
    else:
      print "master param not registerd"
      publish_retCode_and_message(str(204),str("RECIPE:master param not registerd"))
      if(fromUI == False):
        pub_Y3.publish(False)
      return

    # マスターplyファイルパスをfinderに通知 
    pub_model_name.publish(master_ply)

    publish_retCode_and_message(str(0),str("RECIPE:Success"))
    if(fromUI == False):
      print "Call Y3"
      pub_Y3.publish(True)

  except rospy.ServiceException, e:
    print 'cb_recipe:recipe_id failed:',e
    publish_retCode_and_message(str(205),str("RECIPE:failed"))
    if(fromUI == False):
      pub_Y3.publish(False)

  return

##########################################
# RemoveMaster
# 指定されたマスターを削除する。
##########################################
def remove_master_model():
  global recipe_id, master_ply, master_rt, master_param, rovi_param, rcalib_param

  try:
    if(getRecipeIdFromRosParam() == False): # recipe_idが無い場合はエラー
      print "ERROR: remove_master_model:recipe_id failed."
      return 501

    # recipe_idに該当するマスターファイルのパスを作成
    makeMasterFilePath(recipe_id)

    #マスターファイル削除
    if(os.path.exists(master_ply)):
      os.remove(master_ply)  

    #マスターRTファイル削除
    if(os.path.exists(master_rt)):
      os.remove(master_rt)  

    # パラメータファイル及びros paramの削除
    if(os.path.exists(master_param)):
      os.remove(master_param)  

    #バックアップパラメータファイル削除
    if(os.path.exists(rovi_param)):
      os.remove(rovi_param)  

    #rcalibパラメータファイル削除
    if(os.path.exists(rcalib_param)):
      os.remove(rcalib_param)  

  except rospy.ServiceException, e:
    print 'remove_master_model:remove master failed:',e
    return 502

  rospy.set_param('/mt/recipe','')

  return 0

##########################################
# 処理結果コードとメッセージをsocketに送信する
##########################################
def publish_retCode_and_message(retCode,msg):
  print "### publish_retCode_and_message retCode=", retCode, " msg=", msg
  pub_err.publish(retCode)
  sleep(0.001)
  pub_msg.publish(msg)
  # 上記メッセージ送信後1msec待つ
  sleep(0.001)
  return

############################################################################
### call back
############################################################################

##########################################
# phase shiftコールバック  
# 結果をscoketに通知する(Y1)
# 実際の処理はcropperで行うので、ここではmsg.dataが無い場合の処理だけ行う
##########################################
def cb_result_ps(msg):
  global fromUI

  print "### cb_retPs msg=", msg.data

  if(msg.data == "0"):
    publish_retCode_and_message(str(0),str("CROP:Success"))
    if(fromUI == False):
      pub_Y1.publish(True)
  elif(msg.data == "103"):
    publish_retCode_and_message(msg.data,str("CROP:proc_btm_rt file write exception"))
    if(fromUI == False):
      pub_Y1.publish(False)
  elif(msg.data == "104"):
    publish_retCode_and_message(msg.data,str("CROP:crop param not set"))
    if(fromUI == False):
      pub_Y1.publish(False)

##########################################
# clear scene
##########################################
def cb_X0(f):
  print "X0:scene reset"
  
  # cropperにclearをpublishする
  pub_clear.publish(False)

  return

##########################################
# キャプチャーコールバック(ロボットから呼ばれる)
##########################################
def cb_X1(f): 			# キャプyチャー(ロボットから呼ばれる)
  global fromUI
  fromUI = False

  print "##### start cb_X1 " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")

  capture_scene(f)

  print "##### end cb_X1 " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")

  return

##########################################
# キャプチャーコールバック(UIから呼ばれる)
##########################################
def cb_capture_scene(f):  	# キャプチャー(UIから呼ばれる)
  global fromUI
  fromUI = True

  print "##### start cb_capture_scene " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")

  # error_code,messageの初期化
  publish_retCode_and_message("","")

  capture_scene(f)

  print "##### end cb_capture_scene " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")
  return

##########################################
# MasterTeachコールバック(ロボットから呼ばれる)
##########################################
def cb_X2(f):
  global fromUI
  fromUI = False

  print "##### start cb_X2 " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")

  #icp_proc(f)
  pub_solv.publish(f)

  print "##### end cb_X2 " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")
  return

##########################################
# MasterTeachコールバック(UIから呼ばれる)
##########################################
def cb_master_teach(f):
  global fromUI
  fromUI = True

  print "##### start cb_master_teach " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")

  # error_code,messageの初期化
  publish_retCode_and_message("","")

  #####icp_proc(f)
  pub_solv.publish(f)

  print "##### end cb_master_teach " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")

##########################################
# Recipeコールバック(ロボットから呼ばれる)
##########################################
def cb_X3(f):
  global fromUI
  fromUI = False

  print "##### start cb_X3 " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")

  recipe(f)

  print "##### end cb_X3 " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")
  return

##########################################
# Recipeコールバック(UIから呼ばれる)
##########################################
def cb_recipe(f):
  global fromUI
  fromUI = True

  print "##### start cb_recipe " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")

  # error_code,messageの初期化
  publish_retCode_and_message("","")

  recipe(f)

  print "##### end cb_recipe " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")
  return

##########################################
# マスター削除コールバック(UIから呼ばれる)
##########################################
def cb_rem_master_model(f):
  print "##### start cb_remove_master_model " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")

  # error_code,messageの初期化
  publish_retCode_and_message("","")

  ret = remove_master_model()
  if(ret == 501):
    publish_retCode_and_message(str(ret),str("REMOVE MASTER:recipe_id not registerd"))
  elif(ret == 502):
    publish_retCode_and_message(str(ret),str("REMOVE MASTER:remove master failed"))

  # 削除したマスターが現在選択中の場合には、/mt/masterパラメータを削除する
  # パラメータ取得
  # レシピID
  remove_recipe_id = rospy.get_param('/mt/master/recipe_id',None)
  if(remove_recipe_id == None): # recipe_idが無い場合はそのまま終了
    publish_retCode_and_message(str(0),str("REMOVE MASTER:Success"))
    return
  else:
    if(len(recipe_id) == 0): # recipe_idが無い場合はそのまま終了
      publish_retCode_and_message(str(0),str("REMOVE MASTER:Success"))
      return

  # /mt/masterパラメータを削除する
  if rospy.has_param('/mt/master'):
    rospy.delete_param('/mt/master')

  publish_retCode_and_message(str(0),str("REMOVE MASTER:Success"))

  print "##### end cb_remove_master_model " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")
  return

##########################################
# マスター登録（UIから呼ばれる）
##########################################
def cb_reg_master_model(f):
  global recipe_id, master_dir, master_ply, master_rt, master_param, bTmCurrent, scenePn

  print "##### start cb_reg_master_model " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")

  # error_code,messageの初期化
  publish_retCode_and_message("","")

  try:
    # 登録対象のscene
    if(len(scenePn ) == 0): # sceneが無い場合はエラー
      print '### scenePn len is zero' 
      publish_retCode_and_message(str(401),str("REGIST MASTER:scene ply length is zero"))
      return

    # 1枚目の撮影位置
    if(np.sum(bTmCurrent != np.eye(4).astype(float)) ==  0): # 設定されていない場合はエラー
      print "### bTmCurrent is not set!"
      publish_retCode_and_message(str(402),str("REGIST MASTER:bTm is not set"))
      return

    # パラメータ取得
    # レシピID
    if(getRecipeIdFromRosParam() == False): # recipe_idが無い場合はエラー
      print '### recipe_id is None' 
      publish_retCode_and_message(str(403),str("REGIST MASTER:recipe_id not selected"))
      return

    # cameraパラメータ
    camera_exposure_time = rospy.get_param('/rovi/pshift_genpc/camera/ExposureTime',8400)
    camera_gain = rospy.get_param('/rovi/pshift_genpc/camera/Gain',0)

    # projectorパラメータ
    projector_exposure_time = rospy.get_param('/rovi/pshift_genpc/projector/ExposureTime',20)
    projector_intencity = rospy.get_param( '/rovi/pshift_genpc/projector/Intencity',120)
    projector_interval = rospy.get_param('/rovi/pshift_genpc/projector/Interval',50)

    # cropパラメータ(zcrop)
    crop_zcrop_near = rospy.get_param('/cropper/zcrop/near',0)
    crop_zcrop_far = rospy.get_param('/cropper/zcrop/far',0)

    # cropパラメータ(sphere)
    crop_sphere_x = rospy.get_param('/cropper/sphere/x',0)
    crop_sphere_y = rospy.get_param('/cropper/sphere/y',0)
    crop_sphere_r = rospy.get_param('/cropper/sphere/r',0)

    # cropパラメータ(voxel)
    crop_voxel = rospy.get_param('/cropper/voxel',0)

    # cropパラメータ(frame_id)
    crop_frame_id = rospy.get_param('/cropper/frame_id',6)
    
    # RANSAC一致率閾値
    ransac_fitness_threshold = rospy.get_param('/mt/master_param/ransac/fitness_threshold',0.0)

    # RANSAC反復の最大回数
    ransac_max_iteration = rospy.get_param('/mt/master_param/ransac/max_iteration',0.0)

    # RANSAC検証ステップの最大数
    ransac_max_validation = rospy.get_param('/mt/master_param/ransac/max_validation',0.0)

    # ICP一致率閾値
    icp_fitness_threshold = rospy.get_param('/mt/master_param/icp/fitness_threshold',0.0)

    # ロボット移動(X座標)閾値:上限
    translationX_upper_threshold = rospy.get_param('/mt/master_param/icp/translation_threshold/upper_x',0.0)

    # ロボット移動(X座標)閾値:下限
    translationX_lower_threshold = rospy.get_param('/mt/master_param/icp/translation_threshold/lower_x',0.0)

    # ロボット移動(Y座標)閾値:上限
    translationY_upper_threshold = rospy.get_param('/mt/master_param/icp/translation_threshold/upper_y',0.0)

    # ロボット移動(Y座標)閾値:下限
    translationY_lower_threshold = rospy.get_param('/mt/master_param/icp/translation_threshold/lower_y',0.0)

    # ロボット移動(Z座標)閾値:上限
    translationZ_upper_threshold = rospy.get_param('/mt/master_param/icp/translation_threshold/upper_z',0.0)

    # ロボット移動(Z座標)閾値:下限
    translationZ_lower_threshold = rospy.get_param('/mt/master_param/icp/translation_threshold/lower_z',0.0)

    # ロボット回転(X軸)閾値:上限
    rotationEulerA_upper_threshold = rospy.get_param('/mt/master_param/icp/rotation_euler_threshold/upper_a',0.0)

    # ロボット回転(X軸)閾値:下限
    rotationEulerA_lower_threshold = rospy.get_param('/mt/master_param/icp/rotation_euler_threshold/lower_a',0.0)

    # ロボット回転(Y軸)閾値:上限
    rotationEulerB_upper_threshold = rospy.get_param('/mt/master_param/icp/rotation_euler_threshold/upper_b',0.0)

    # ロボット回転(Y軸)閾値:下限
    rotationEulerB_lower_threshold = rospy.get_param('/mt/master_param/icp/rotation_euler_threshold/lower_b',0.0)

    # ロボット回転(Z軸)閾値:上限
    rotationEulerC_upper_threshold = rospy.get_param('/mt/master_param/icp/rotation_euler_threshold/upper_c',0.0)

    # ロボット回転(Z軸)閾値:下限
    rotationEulerC_lower_threshold = rospy.get_param('/mt/master_param/icp/rotation_euler_threshold/lower_c',0.0)

    # マッチングアルゴリズム(1:ICP その他は未定)
    algor = rospy.get_param('/mt/master_param/algor',1)

    print "reg_master_model:recipe_id=", recipe_id
    print "reg_master_model:camera_exposure_time=", camera_exposure_time
    print "reg_master_model:camera_gain=", camera_gain
    print "reg_master_model:projector_exposure_time=", projector_exposure_time
    print "reg_master_model:projector_intencity=", projector_intencity
    print "reg_master_model:projector_interval=", projector_interval
    print "reg_master_model:crop_zcorp_near=", crop_zcrop_near, " crop_zcor_far=", crop_zcrop_far
    print "reg_master_model:crop_sphere_x=", crop_sphere_x, " crop_sphere_y=", crop_sphere_y, " crop_sphere_r=", crop_sphere_r
    print "reg_master_model:crop_voxel=", crop_voxel
    print "reg_master_model:crop_frame_id=", crop_frame_id
    print "reg_master_model:ransac_fitness_threshold=", ransac_fitness_threshold
    print "reg_master_model:ransac_max_iteration=", ransac_max_iteration
    print "reg_master_model:ransac_max_validation=", ransac_max_validation
    print "reg_master_model:icp_fitness_threshold=", icp_fitness_threshold
    print "reg_master_model:translationX_upper_threshold=", translationX_upper_threshold
    print "reg_master_model:translationX_lower_threshold=", translationX_lower_threshold
    print "reg_master_model:translationY_upper_threshold=", translationY_upper_threshold
    print "reg_master_model:translationY_lowerthreshold=", translationY_lower_threshold
    print "reg_master_model:translationZ_upper_threshold=", translationZ_upper_threshold
    print "reg_master_model:translationZ_lower_threshold=", translationZ_lower_threshold
    print "reg_master_model:rotationEulerA_upper_threshold=", rotationEulerA_upper_threshold
    print "reg_master_model:rotationEulerA_lower_threshold=", rotationEulerA_lower_threshold
    print "reg_master_model:rotationEulerB_upper_threshold=", rotationEulerB_upper_threshold
    print "reg_master_model:rotationEulerB_lower_threshold=", rotationEulerB_lower_threshold
    print "reg_master_model:rotationEulerC_upper_threshold=", rotationEulerC_upper_threshold
    print "reg_master_model:rotationEulerC_lower_threshold=", rotationEulerC_lower_threshold
    print "reg_master_model:algor=", algor

    # recipe_idに該当するマスターファイルのパスを作成
    makeMasterFilePath(recipe_id)

    # マスターが登録済みの場合はエラー
    if(isMasterRegisterd() == True):
      print 'ERROR: reg_master_model master is registerd'
      publish_retCode_and_message(str(404),str("REGIST MASTER:master is already registerd"))
      return

    #マスターファイル保存ディレクトリが無ければ作っておく
    if(not os.path.isdir(master_dir)):
      os.mkdir(master_dir) 

    # 現在のbTm
    print "reg_master_model bTmCurrent:\n", bTmCurrent


    ##############################################################
    ## マスター点群書き出し
    ## 残すのは出力座標系で指定された座標系に変換された点群ファイルとICPからのRT
    ##############################################################
    print "make Master PLY file."

    # マスター点群ファイルの書き出し
    cv2.ppf_match_3d.writePLY(scenePn.astype(np.float32), master_ply)

    # マスターRT（ロボット座標）ファイルの書き出し
    print "write Master RT file."

    try:
      with open(master_rt, 'wb') as f:
        pickle.dump(bTmCurrent, f)
    except Exception as e:
      print "master_rt file write exception: ", e
      publish_retCode_and_message(str(405),str("REGIST MASTER:master rt file write exeption"))
      return

    # マスターパラメータ（fitness_threshold,exposure_time,gainなどを保存している)ファイルの書き出し
    print "write Master Param file."

    try:
      exposure_time = rospy.get_param(rovi_exposure_time_field_path,8400)
      gain = rospy.get_param(rovi_gain_field_path,0)
      projector_exposure_time = rospy.get_param(rovi_projector_exposure_time_field_path,20)
      projector_intencity = rospy.get_param(rovi_projector_intencity_field_path,120)
      projector_interval = rospy.get_param(rovi_projector_interval_field_path,50)

      with open(master_param, 'w') as f:
        s = 'mt:\n'
        f.write(s)
        s = '  master:\n'
        f.write(s)
        s = '    recipe_id: ' + str(recipe_id) + '\n'
        f.write(s)
        s = '    ransac:\n'
        f.write(s)
        s = '      fitness_threshold: ' + str(ransac_fitness_threshold) + '\n'
        f.write(s)
        s = '      max_iteration: ' + str(ransac_max_iteration) + '\n'
        f.write(s)
        s = '      max_validation: ' + str(ransac_max_validation) + '\n'
        f.write(s)
        s = '    icp:\n'
        f.write(s)
        s = '      fitness_threshold: ' + str(icp_fitness_threshold) + '\n'
        f.write(s)
        s = '      translation_threshold:\n'
        f.write(s)
        s = '        upper_x: ' + str(translationX_upper_threshold) + '\n'
        f.write(s)
        s = '        lower_x: ' + str(translationX_lower_threshold) + '\n'
        f.write(s)
        s = '        upper_y: ' + str(translationY_upper_threshold) + '\n'
        f.write(s)
        s = '        lower_y: ' + str(translationY_lower_threshold) + '\n'
        f.write(s)
        s = '        upper_z: ' + str(translationZ_upper_threshold) + '\n'
        f.write(s)
        s = '        lower_z: ' + str(translationZ_lower_threshold) + '\n'
        f.write(s)
        s = '      rotation_euler_threshold:\n'
        f.write(s)
        s = '        upper_a: ' + str(rotationEulerA_upper_threshold) + '\n'
        f.write(s)
        s = '        lower_a: ' + str(rotationEulerA_lower_threshold) + '\n'
        f.write(s)
        s = '        upper_b: ' + str(rotationEulerB_upper_threshold) + '\n'
        f.write(s)
        s = '        lower_b: ' + str(rotationEulerB_lower_threshold) + '\n'
        f.write(s)
        s = '        upper_c: ' + str(rotationEulerC_upper_threshold) + '\n'
        f.write(s)
        s = '        lower_c: ' + str(rotationEulerC_lower_threshold) + '\n'
        f.write(s)
        s = '    camera:\n'
        f.write(s)
        s = '      exposure_time: ' + str(camera_exposure_time) + '\n'
        f.write(s)
        s = '      gain: ' + str(camera_gain) + '\n'
        f.write(s)
        s = '    projector:\n'
        f.write(s)
        s = '      exposure_time: ' + str(projector_exposure_time) + '\n'
        f.write(s)
        s = '      intencity: ' + str(projector_intencity) + '\n'
        f.write(s)
        s = '      interval: ' + str(projector_interval) + '\n'
        f.write(s)
        s = '    cropper:\n'
        f.write(s)
        s = '      zcrop:\n'
        f.write(s)
        s = '        near: ' + str(crop_zcrop_near) + '\n'
        f.write(s)
        s = '        far: ' + str(crop_zcrop_far) + '\n'
        f.write(s)
        s = '      sphere:\n'
        f.write(s)
        s = '        x: ' + str(crop_sphere_x) + '\n'
        f.write(s)
        s = '        y: ' + str(crop_sphere_y) + '\n'
        f.write(s)
        s = '        r: ' + str(crop_sphere_r) + '\n'
        f.write(s)
        s = '      voxel: ' + str(crop_voxel) + '\n'
        f.write(s)
        s = '      frame_id: ' + str(crop_frame_id) + '\n'
        f.write(s)
        s = '    algor: ' + str(algor) + '\n'
        f.write(s)
    except Exception as e:
      print "ERROR: master_param file write exception: ", e
      publish_retCode_and_message(str(406),str("REGIST MASTER:master param file write exeption"))
      remove_master_model()
      return

    # バックアップパラメータ（/rovi配下を保存している)ファイルの書き出し 
    # 処理で使うことはない
    print "write rovi Param file."
    try:
      if rospy.has_param('/rovi'):
        rovi_param_data = rospy.get_param('/rovi')
        with open(rovi_param,'w') as f:
          yaml.dump(rovi_param_data,f)
      else:
        print "ERROR: rovi_param not found: ", e
        publish_retCode_and_message(str(407),str("REGIST MASTER:rovi param not found"))
        remove_master_model()

    except Exception as e:
      print "ERROR: rovi_param file write exception: ", e
      publish_retCode_and_message(str(408),str("REGIST MASTER:rovi param file write exeption"))
      remove_master_model()
      return

    # キャリブパラメータ（HOME/.ros/rcalib.yaml)ファイルの書き出し 
    # 処理で使うことはない
    print "copy rcalib.yaml file."
    try:
      if(os.path.exists(rcalib_yaml_path)): #ベース座標点群 (クロップ後の点群)
        shutil.copy(rcalib_yaml_path,rcalib_param)
      else:
        print "ERROR: rcalib.yaml file not found"
        publish_retCode_and_message(str(409),str("REGIST MASTER:rcalib.yaml not found"))
        remove_master_model()

    except Exception as e:
      print "ERROR: rcalib_param file write exception: ", e
      publish_retCode_and_message(str(410),str("REGIST MASTER:rcalib.yaml file write exeption"))
      remove_master_model()
      return

  except rospy.ServiceException, e:
    print 'ERROR: reg_master_model failed:',e
    publish_retCode_and_message(str(411),str("REGIST MASTER:regist master model exeption"))
    remove_master_model()

  publish_retCode_and_message(str(0),str("REGIST MASTER:Success"))
  print "##### end cb_reg_master_model " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")

  return

##########################################
# 合成点群(クロップ後の点群)受信 座標系はcropper/frame_idで指定された出力座標系
##########################################
def cb_scene(msg):
  global scenePn

  print "cb_scene called!"

  print "#####  start cb_scene " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")

  # 撮影した点群を取得する
  P=np.reshape(msg.data,(-1,3))

  # 撮影した点群を保存しておく
  scenePn = P

  print '###### scenePn shape=', scenePn.shape
  print '###### size=', np.prod(scenePn.shape)
  print '###### len=', len(scenePn)

  print "#####  end cb_scene " +datetime.datetime.today().strftime("%Y_%m_%d_%H%M%S")

  return

##########################################
# ロボット座標受信
##########################################
def cb_scene_tf(tf):
  global bTmCurrent
  
  print "cb_scene_tf called!"

  bTmCurrent=tflib.toRT(tf)

  print 'cb_scene_tf bTmCurrent:\n', bTmCurrent

  return

##########################################
# マスターティーチの処理結果(finderから通知される)
##########################################
def cb_resultrt(msg):
  global error_code, proc_mssage, fromUI

  print "cb_result_master_teach called!"
  print "cb_result_master_teach msg len=", len(msg.data)

  #rt[1,16]を[4,4]に変換
  RT = np.array(msg.data).reshape([4,4])
  print "cb_result_master_teach RT=", RT

  size = np.prod(RT.shape)
  f = Floats()
  f.data = np2F(RT.reshape(1,size)).data

  pub_RT.publish(f)
  publish_retCode_and_message(str(error_code),str(proc_message))
  if(fromUI == False):
    pub_Y2.publish(True)

  return

##########################################
# エラーコード(finderから通知される)
##########################################
def cb_error(msg):
  global error_code
  error_code = int(msg.data)
  print "cb_error: error_code=",error_code
  return

##########################################
# 処理メッセージ(finderから通知される)
##########################################
def cb_message(msg):
  global proc_message
  proc_message = msg.data
  print "cb_message: proc_message=",proc_message
  return

##########################################
# error_code及びmessageをクリアする(socketまたはfinderから通知される)
##########################################
def cb_error_reset(f):
  print "### cb_error_reset called"
  publish_retCode_and_message("","")
  return

########################################################

###Input topics(subscribe)
rospy.Subscriber("/solver/capture",Bool,cb_capture_scene)					# Capture and genpc into scene（UIから呼ばれる）
rospy.Subscriber("/mt/source/scene/floats",numpy_msg(Floats),cb_scene)				# 合成点群(cropperがpublishする) 座標系はcropper/frame_idで指定された出力座標系
rospy.Subscriber("/mt/source/tf",Transform,cb_scene_tf)						# 1枚目撮影位置(ロボット座標)
rospy.Subscriber("/result_ps",String,cb_result_ps)						# phase shift処理コールバック(cropperがpublishする)
rospy.Subscriber("/mt/regMaster",Bool,cb_reg_master_model)					# マスター登録（UIから呼ばれる） 
rospy.Subscriber("/mt/remMaster",Bool,cb_rem_master_model)					# マスター削除（UIから呼ばれる） 
rospy.Subscriber("/mt/recipe",Bool,cb_recipe)							# RECIPE 選択 /mt/recipe に設定されたrecipe_idが選択されたものとする。(UIから呼ばれる）
rospy.Subscriber("/mt/master_teach",Bool,cb_master_teach)					# Recognize work and calc picking pose（UIから呼ばれる）
rospy.Subscriber("/mt/icpresult/rt",numpy_msg(Floats),cb_resultrt)				# マスターティーチの処理結果(finderから通知される)
rospy.Subscriber("/mt/message",String,cb_message)						# 処理結果メッセージ(finderから通知される)
rospy.Subscriber("/mt/error",String,cb_error)							# 処理結果コード(finderら通知される)
rospy.Subscriber("/mt/reset",Bool,cb_error_reset)						# error_code及びmessageをクリアする (finderから通知される)

###### from robot(js経由)
##rospy.Subscriber("/robot/tf",Transform,cb_tf)							# ロボットからロボット座標を受け取る
##rospy.Subscriber("/robot/euler",Transform,cb_tf2) 						# ロボット座標を受け取る（オフライン用 rqtから呼ばれる） 
##rospy.Subscriber("/rovi/ps_floats",numpy_msg(Floats),cb_ps)					# phase shift処理コールバック
rospy.Subscriber("/robot/X0",Bool,cb_X0)							# Clear scene
rospy.Subscriber("/robot/X1",Bool,cb_X1)							# Capture and genpc into scene
rospy.Subscriber("/robot/X2",Bool,cb_X2)							# Recognize work and calc picking pose
rospy.Subscriber("/robot/X3",Bool,cb_X3)							# RECIPE 選択 /mt/recipe に設定されたrecipe_idが選択されたものとする。
rospy.Subscriber("/robot/reset",Bool,cb_error_reset)						# error_code及びmessageをクリアする 

###Params
master_dir = rospy.get_param('/mt/master_dir')							# マスターデータ格納ディレクトリ

xmin = float(rospy.get_param('/volume_of_interest/xmin'))
xmax = float(rospy.get_param('/volume_of_interest/xmax'))
ymin = float(rospy.get_param('/volume_of_interest/ymin'))
ymax = float(rospy.get_param('/volume_of_interest/ymax'))
zmin = float(rospy.get_param('/volume_of_interest/zmin'))
zmax = float(rospy.get_param('/volume_of_interest/zmax'))
sparse_threshold = int(rospy.get_param('/dense_sparse/threshold'))

print "xmin=", xmin, "xmax=", xmax, "ymin=", ymin, "ymax=", ymax, "zmin=", zmin, "zmax=", zmax
print "sparse_threshold=", sparse_threshold
'''
print("master_dir:",master_dir)
'''

###Output topics
pub_clear=rospy.Publisher("/clear",Bool,queue_size=1)							# clear scene
pub_model_name=rospy.Publisher('/mt/model/name',String,queue_size=1)					# モデルの点群ファイルパス
pub_model_tf=rospy.Publisher('/mt/model/tf',Transform,queue_size=1)					# モデルのロボット座標(1枚目撮影時の位置) 
pub_model_algor=rospy.Publisher('/mt/model/algor',String,queue_size=1)					# モデルのマッチングアルゴリズム
pub_solv=rospy.Publisher('/mt/solv',Bool,queue_size=1)							# マスターティーチ実行

###### to robot(js経由)
pub_Y1=rospy.Publisher('/robot/Y1',Bool,queue_size=1)    						# X1 done
pub_Y2=rospy.Publisher('/robot/Y2',Bool,queue_size=1)    					   	# X2 done RT から tfへの変換はsocket(js)側で行う
pub_Y3=rospy.Publisher('/robot/Y3',Bool,queue_size=1)    						# X3 done 
pub_RT=rospy.Publisher('/robot/result_rt',numpy_msg(Floats),queue_size=1) 				# X2 done RTをsocketに通知
pub_msg=rospy.Publisher('/solver/message',String,queue_size=1)    					# 処理結果メッセージを通知(socket及びrqt_param_manager)
pub_err=rospy.Publisher('/solver/error',String,queue_size=1)						# error_codeを通知(socket及びrqt_param_manager)

###Transform
bTmLat=np.eye(4).astype(float)  #robot RT when captured
bTm=np.eye(4).astype(float) 
cTs=np.eye(4,dtype=float)
bTc=np.eye(4,dtype=float)
bTmCurrent=np.eye(4).astype(float)  #robot RT when captured

###Robot Calibration Result
mTc=tflib.toRT(tflib.dict2tf(rospy.get_param('/robot/calib/mTc')))  # arM tip To Camera
#print "mTc=", mTc

###Globals
recipe_id = ''			# レシピID
master_ply = ''			# マスター点群ファイル名
master_rt = ''			# マスターRTファイル名
master_param = ''		# マスターパラメータファイル名
rovi_param = ''			# バックアップパラメータファイル名(/rovi以下のパラメータをバックアップしている)
rcalib_param = ''		# キャリブパラメータファイル名(HOME/.ros/rcalib.yamlをバックアップしている)
error_code = 0			# error code(0が正常)
proc_message = ''		# 処理メッセージ
dateStr = ''			# デバッグ表示用(日時表示用)
fromUI = False 			# UIから呼ばれた場合はTrue,ロボットから呼ばれた場合はFalse (UIから呼ばれた場合にロボットに応答しないためのフラグ)

###Initialize
# /mt/masterパラメータを削除する
if rospy.has_param('/mt/master'):
  rospy.delete_param('/mt/master')

def masterteach():
  rospy.init_node("master_teach",anonymous=True)

  try:
    rospy.spin()
  except KeyboardInterrupt:
    print "Shutting down"

if __name__ == '__main__':
  masterteach()



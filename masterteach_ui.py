#!/usr/bin/python
# -*- coding: utf-8 -*-

import cv2
import numpy as np
import roslib
import rospy
from std_msgs.msg import Bool
from std_msgs.msg import String
from geometry_msgs.msg import Transform
from rovi.msg import MasterParam	# マスターパラメータ(テスト用)
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), os.environ['ROVI_PATH'] + '/script'))
import tflib

def cb_X0(f):
  print 'CLEAR SCENE'
  f=Bool()
  pub_X0.publish(f)
  return

def cb_capt(tf):
  print 'CAPTURE SCENE'
  pub_euler.publish(tf)
  f=Bool()
  pub_capture.publish(f)
  return

def cb_master_teach(f):
  print 'MATCH SCENE'
  f=Bool()
  pub_master_teach.publish(f)
  return

def cb_recipe(f):
  print 'RECIPE'
  pub_recipe.publish(f)
  return

def cb_set_recipe(id):
  print 'SET RECIPE ID'
  # パラメータ登録
  # recipeId
  s = '/mt/recipe'
  rospy.set_param(s,str(id.data))
  return

def cb_set_master_param(rm):
  print 'SET MASTER PARAM'

  # パラメータ登録
  # RANSAC一致率閾値
  s = '/mt/master_param/ransac/fitness_threshold'
  rospy.set_param(s,rm.ransac_fitness_threshold)
  # RANSAC反復の最大回数
  s = '/mt/master_param/ransac/max_iteration'
  rospy.set_param(s,rm.ransac_max_iteration)
  # RANSAC検証ステップの最大数
  s = '/mt/master_param/ransac/max_validation'
  rospy.set_param(s,rm.ransac_max_validation)
  # ICP一致率閾値
  s = '/mt/master_param/icp/fitness_threshold'
  rospy.set_param(s,rm.fitness_threshold)
  # ロボット移動(X座標)閾値:上限
  s = '/mt/master_param/icp/translation_threshold/upper_x'
  rospy.set_param(s,rm.translationX_upper_threshold)
  # ロボット移動(X座標)閾値:下限
  s = '/mt/master_param/icp/translation_threshold/lower_x'
  rospy.set_param(s,rm.translationX_lower_threshold)
  # ロボット移動(Y座標)閾値:上限
  s = '/mt/master_param/icp/translation_threshold/upper_y'
  rospy.set_param(s,rm.translationY_upper_threshold)
  # ロボット移動(Y座標)閾値:下限
  s = '/mt/master_param/icp/translation_threshold/lower_y'
  rospy.set_param(s,rm.translationY_lower_threshold)
  # ロボット移動(Z座標)閾値:上限
  s = '/mt/master_param/icp/translation_threshold/upper_z'
  rospy.set_param(s,rm.translationZ_upper_threshold)
  # ロボット移動(Z座標)閾値:下限
  s = '/mt/master_param/icp/translation_threshold/lower_z'
  rospy.set_param(s,rm.translationZ_lower_threshold)
  # ロボット回転(X軸)閾値:上限
  s = '/mt/master_param/icp/rotation_euler_threshold/upper_a'
  rospy.set_param(s,rm.rotationEulerA_upper_threshold)
  # ロボット回転(X軸)閾値:下限
  s = '/mt/master_param/icp/rotation_euler_threshold/lower_a'
  rospy.set_param(s,rm.rotationEulerA_lower_threshold)
  # ロボット回転(Y軸)閾値:上限
  s = '/mt/master_param/icp/rotation_euler_threshold/upper_b'
  rospy.set_param(s,rm.rotationEulerB_upper_threshold)
  # ロボット回転(Y軸)閾値:下限
  s = '/mt/master_param/icp/rotation_euler_threshold/lower_b'
  rospy.set_param(s,rm.rotationEulerB_lower_threshold)
  # ロボット回転(Z軸)閾値:上限
  s = '/mt/master_param/icp/rotation_euler_threshold/upper_c'
  rospy.set_param(s,rm.rotationEulerC_upper_threshold)
  # ロボット回転(Z軸)閾値:下限
  s = '/mt/master_param/icp/rotation_euler_threshold/lower_c'
  rospy.set_param(s,rm.rotationEulerC_lower_threshold)
  # マッチングアルゴリズム(1:ICP その他は未定)
  s = '/mt/master_param/algor'
  rospy.set_param(s,rm.algor)

  return

def cb_regist_master_model(f):
  print 'REGISTRATION MASTER MODEL'
  # /mt/regMasterをpublish
  f=Bool()
  pub_regist_master.publish(f)
  return

def cb_remove_master_model(f):
  print 'REMOVE MASTER MODEL'
  f=Bool()
  pub_remove_master.publish(f)
  return

########################################################

rospy.init_node("ui",anonymous=True)
###Input topics
rospy.Subscriber("clear_scene",Bool,cb_X0)								#clear scene
rospy.Subscriber("set_master_param",MasterParam,cb_set_master_param)				 	#set master param
rospy.Subscriber("registration_master_model",Bool,cb_regist_master_model)			 	#regist master model
rospy.Subscriber("remove_master_model",Bool,cb_remove_master_model)					#remove master model
rospy.Subscriber("set_recipe",String,cb_set_recipe)							#set recipe id
rospy.Subscriber("recipe",Bool,cb_recipe)								#recipe
rospy.Subscriber("capture_scene",Transform,cb_capt)							#capture
rospy.Subscriber("master_teach",Bool,cb_master_teach)							#master teach

###Output topics
pub_euler=rospy.Publisher("/robot/euler",Transform,queue_size=1)
pub_X0=rospy.Publisher("/solver/X0",Bool,queue_size=1)    						#clear scene
pub_capture=rospy.Publisher("/solver/capture",Bool,queue_size=1)					#capure
pub_regist_master=rospy.Publisher("/mt/regMaster",Bool,queue_size=1)					#regist master model
pub_remove_master=rospy.Publisher("/mt/remMaster",Bool,queue_size=1)					#remmove master model
pub_recipe=rospy.Publisher("/mt/recipe",Bool,queue_size=1)						#recipe
pub_master_teach=rospy.Publisher("/mt/master_teach",Bool,queue_size=1)					#master teach

try:
  rospy.spin()
except KeyboardInterrupt:
  print "Shutting down"

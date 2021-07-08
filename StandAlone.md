# Stand Alone 版での変更箇所
1. dashboard.yaml  
loadで指定する、追加ロードするロボットのyamlをストリーミングなしのロボットにする。とりあえず川重を流用。
~~~
config:
  dashboard:
    load: rovi_visual_teach/rc.d/kw.yaml
~~~
2. kw.launch(@rovi_industrial)  
YCAM位置をViewerに表示するためkw.launchに以下を追加
~~~
  <node pkg="rovi_industrial" type="ycam3.py" name="" />
~~~
3. rcalib.yaml  
YCAMを見やすい位置に置くため、ロボットtool0に固定値を設定する。rcalib.yamlに寄生させておこう。
~~~
config_tf:
  camera:
～カメラのキャリブ結果～
  tool0_controller:
    transform:
      rotation:
        w: 0
        x: 0
        y: 0
        z: 0
      translation:
        x: 0
        y: 0
        z: 500   #カメラをグリッドの上空500mmに置く
~~~

4. Rvizの設定  
下図のように表示されます。Viewは"XYOrbit"にしています。
![rviz_settings](https://user-images.githubusercontent.com/5061483/124577295-15f18380-de88-11eb-94f6-1b152e93a0f4.jpg)

5. picker.py  
カメラ座標での移動量を、物体付近の座標系にて出力(reportとTF)されるよう変更。  
Paramにキー"wd"を追加
~~~
 Param={
      :
+  "wd":0
 }
~~~
wdはカメラの撮像距離を表す。WD>0のときは、カメラからWDだけ前方の位置を移動量の基点とする新たなTFを作る(camera/capture0/wd)ようにcb_statsに以下を追加。
~~~
        :
  tf.transform.rotation.w=Stats["Qw"][pick]
  btf=[tf]
  if Param["wd"]>0:
    cTw=getRT(Config["base_frame_id"],Config["solve_frame_id"])
    cTw[0,3]=0
    cTw[1,3]=0
    cTw[2,3]=Param["wd"]
    tfw=copy.deepcopy(tf)
    tfw.header.frame_id=Config["solve_frame_id"]
    tfw.child_frame_id=Config["solve_frame_id"]+"/wd"
    tfw.transform=tflib.fromRT(cTw)
    btf.append(tfw)    
    wTc=np.linalg.inv(cTw)
    cTc=tflib.toRT(tf.transform)
    tfws=copy.deepcopy(tf)
    tfws.header.frame_id=Config["solve_frame_id"]+"/wd"
    tfws.child_frame_id=Config["solve_frame_id"]+"/wd/solve0"
    tfws.transform=tflib.fromRT(wTc.dot(cTc).dot(cTw))
    btf.append(tfws)
    stats["Gx"]=tfws.transform.translation.x
    stats["Gy"]=tfws.transform.translation.y
    stats["Gz"]=tfws.transform.translation.z  
  broadcaster.sendTransform(btf)
  pub_report.publish(str(stats))
            👍 
~~~

WD=500でのソルブ結果は以下のような表示となる
![solve](https://user-images.githubusercontent.com/5061483/124724091-a55d6c00-df46-11eb-9fb6-ff2aac64dec9.png)
新しいTF(camera/capture0/wd)が対象物あたりに来るように、Viewerを見ながらWDの値を調整する。これによって物体の移動量を出力する。

6. setupV2.zui  
WDを入力するためにパネルに項目を追加。
~~~
"class":"Title",  "label":"3.解析チェック"
"class":"Number", "name":"/picker/wd","label":"カメラ距離"
"class":"Pub",    "name":"/request/solve","label":"解析"
~~~
解析ボタンの上に「カメラ距離」という項目を追加しましたが、そもそもそこだろうか？(名称も微妙)

7. conf.d/config.yaml  
最後にレポートに移動量を表示するため以下変更
~~~
  report:
    "altitude": -25
    "width": 1920
    "rows": 4
    recipe: "/dashboard/recipe"
    keys: ["pcount","fitness","rmse","azimuth","rotation","Gx","Gy","Gz","tcap","tfeat","tmatch"]
    labels: ["点数","一致度","平均誤差","傾き","回転","X移動","Y移動","Z移動","撮影処理時間","特徴処理時間","マッチング処理時間"]
~~~
以下のように結果表示される
![report](https://user-images.githubusercontent.com/5061483/124724317-ddfd4580-df46-11eb-9775-e367496fad4f.png)

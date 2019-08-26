# MasterTeach

## 設計

### ユースケース
![usecase](uml/usecase.png)

### 要件(ユースケース補足)
- 3とおりの機器構成

||カメラ|対象物体|
|:----|:----|:----|
|1|ロボット|固定|
|2|固定|ロボット|
|3|固定|固定|

- 構成1,2での点群合成機能
- 構成1でのマウントポイント指定(J6,J5...)
- ソルバー選択機能

### オブジェクト図
![object](uml/object.png)

## 運用

### 準備  
以下をCheckoutしてBuildします。
- [rovi(コア)](https://github.com/YOODS/rovi)
- [rovi_utils(ユーティティ)](https://github.com/YOODS/rovi_utils)
- [rqt_parm_manager(パラメータ編集ツール)](https://github.com/YOODS/rqt_param_manager)
- pip install tkfilebrowser --user
### Launch  
#### メイン
~~~
roslaunch rovi_master_teach main.launch
~~~
#### 段取り  
撮像調整、マスター登録など
~~~
roslaunch rovi_master_teach setup.launch
~~~
**使用する前に...**
1. ロボットドライバーの起動
2. [ロボットキャリブレーション](https://github.com/YOODS/rovi_utils/tree/master/r-calib)  
が必要です。
#### デモの起動
~~~
roslaunch rovi_master_teach demo.launch
~~~


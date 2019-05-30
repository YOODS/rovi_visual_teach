## MasterTeach

### 要件
- 範囲は、Industrial Robot I/F,Searcher,Cropperの管理と、それらのUI(rqt_param_manager)
- ３とおりの機器構成

||カメラ|対象物体|
|:----|:----|:----|
|1|ロボット|固定|
|2|固定|ロボット|
|3|固定|固定|

- 構成1,2での点群合成機能
- 構成1でのマウントポイント指定(J6,J5...)
- ソルバー選択機能
- 表示出力(○:要,×:不要)

|分類|本来の座標系|取り得る座標系|
|:----|:----|:----|
|モデル点群|×master/camera|○capture/camera<br>○world|
|モデル点群(移動後)|-|○capture/camera<br>○world|
|シーン点群|○capure/camera|○world|

- 出力座標系はcapure/cameraとworldで切り替える
- searcherはcapture/cameraで処理し、float2pcで座標変換する(機能追加)

- !!TMCバリエーション!!

|分類|本来の座標系|取り得る座標系|
|:----|:----|:----|
|モデル点群|×master/flange|○capture/flange|
|モデル点群(移動後)|-|○capture/flange|
|シーン点群|○capure/flange||

- searcherはcapure/flange(==master/flange)で処理し、表示もこれのみでよい

### 処理の定義  

| 名前                           | 説明                                                         | PublishされるTopic |
| :----------------------------- | :----------------------------------------------------------- | :----------------- |
| Clear                          | 点群配列をクリアする。                                       |                    |


### Topics(to subscribe)  

| Topic               | タイプ    | 説明                                                         |
| :------------------ | :-------- | :----------------------------------------------------------- |
| /solver/capture     | Bool      | UIからの撮像命令                                             |
| source/scene/floats | Floats    | シーン合成点群データ。cropperから通知される。座標系は**/cropper/frame_id**で指定された座標系。 |
| source/tf           | Transform | 1枚目撮影位置(ロボット座標)。cropperから通知される。         |
| /result_ps          | String    | Cropperの処理結果。cropperから通知される。                   |
| regMaster           | Bool      | マスター登録処理。rqt_param_managerから通知される。/mt/recipeで入力されたレシピIDが処理対象。 |
| remMaster           | Bool      | マスター削除処理。rqt_param_nanagerから通知される。/mt/recipeで入力されたレシピIDが処理対象。 |
| recipe              | Bool      | モデル(レシピ)選択。rqt_param_managerから通知される。/mt/recipeで入力されたレシピIDが処理対象。 |
| master_teach        | Bool      | マスターティーチ実行。rqt_param_managerから通知される。      |
| icpresult/rt        | Floats    | マスターティーチ結果(差分座標)。finderから通知される。       |
| message             | String    | 処理結果メッセージ。finderから通知される。                   |
| error               | String    | 処理結果コード。finderから通知される。                       |
| reset               | Bool      | 処理結果メッセージ、処理結果コードの初期化。finderから通知される。 |
| /robot/X0           | Bool      | Clear処理。Industrial Robot I/Fから通知される。              |
| /robot/X1           | Bool      | 撮像命令。Industrial Robot I/Fから通知される。               |
| /robot/X2           | Bool      | マスターティーチ実行。Industrial Robot I/Fから通知される。   |
| /robot/X3           | Bool      | モデル(レシピ)選択。Industrial Robot I/Fから通知される。/mt/recipeで入力されたレシピIDが処理対象。 |
| /robot/reset        | Bool      | 処理結果メッセージ、処理結果コードの初期化。Industrial Robot I/Fから通知される。 |

### Topics(to publish)  

| Topic       | タイプ    | 説明                                                  |
| :---------- | :-------- | :---------------------------------------------------- |
| /crear      | Bool      | Clear処理。cropper,finderに通知する。 |
| model/name  | String    | モデルのplyファイル名。finderに通知する。             |
| model/tf    | Transform | モデル撮影時(1枚目)のロボット座標。finderに通知する。 |
| model/algor | String    | マッチングアルゴリズムID。finderに通知する。          |
| solv        | Bool      | マスターティーチの実行。finderに通知する。            |
| /robot/Y1   | Bool      | 撮像の終了。Industrial Robot I/Fに通知する。    |
| /robot/Y2   | Bool      | マスターティーチ終了。Industrial Robot I/Fに通知する。            |
| /robot/Y3   | Bool      | レシピ選択の終了。Industrial Robot I/Fに通知する。            |
| /robot/result_rt        | Bool      | マスターティーチ実行後の差分RT**※1**。Industrial Robot I/Fに通知する。            |
| /solver/message        | Bool      | 処理結果メッセージ。。Industrial Robot I/Fに通知する。            |
| /solver/error          | Bool      | 処理結果コード。Industrial Robot I/Fに通知する。            |

### Parameters(this)

| Parameter    | 説明                               |
| :----------- | :--------------------------------- |
| master_dir   | モデル保存フォルダパス             |
| recipe       | 処理対象のレシピID                 |
| model/tf     | Voxelサイズ                        |
| frame_id     | 出力座標系名                       |
| master_param | モデル登録用パラメータ**※2**       |
| master       | 選択されたモデルのパラメータ**※3** |

### Parameters(ref.)

| Parameter                                 | 説明                                  |      |
| :---------------------------------------- | :------------------------------------ | ---- |
| /rovi/pshift_genpc/camera/ExposureTIme    | カメラ：露光時間                      |      |
| /rovi/pshift_genpc/projector/Gain         | カメラ：ゲイン                        |      |
| /rovi/pshift_genpc/projector/ExposureTime | プロジェクター：露光時間              |      |
| /rovi/pshift_genpc/projector/Intencity    | プロジェクター：発光強度              |      |
| /rovi/pshift_genpc/projector/Interval     | プロジェクター：発光間隔              |      |
| /cropper/zcorp/near                       | Z方向クロップパラメータ：カメラ側     |      |
| /cropper/zcorp/far                        | Z方向クロップパラメータ：床側         |      |
| /cropper/sphere/x                         | XY平面円クロップパラメータ：中心X座標 |      |
| /cropper/sphere/y                         | XY平面円クロップパラメータ：中心Y座標 |      |
| /cropper/sphere/r                         | XY平面円クロップパラメータ：半径      |      |
| /cropper/voxel                            | クロップパラメータ：voxelサイズ       |      |
| /cropper/frame_id                         | クロップパラメータ：出力座標系**※4**        |      |

**※1** RT：座標・回転行列

**※2** master_param(モデル登録用パラメータ)

| Parameter(大項目) | Parameter(中項目)     | Parameter(小項目)                                                   |説明      |
| ----------------- | --------------------- | ------------------------------------------------------ | ---- |
| ransac            |     |                            | ransacパラメータ       |
|             | fitness_threshold     |                            | ransacを終了するfitness閾値       |
|                   | max_iteration         |                                          | 反復の最大回数      |
|                   | max_validation        |                                    | 検証ステップの最大数     |
| icp               |     |  | ICPパラメータ     |
|                | fitness_threshold     |  | ICP一致率閾値（この値未満の場合にはICPの結果NGを返す）     |
|                   | translation_threshold |                                                        | ICP算出位置をロボットに通知する際の閾値<br />(組となっているupper,lowerが両方0の場合には閾値判定しない) |
|                   |                       | upper_x<br />lower_x | X座標上下限値 |
| | | upper_y<br />lower_y | Y座標上下限値 |
| | | upper_z<br />lower_z | Z座標上下限値 |
| | rotation_euler_threshold |  | ICP算出位置をロボットに通知する際の閾値(組となっているupper,lowerが両方0の場合には閾値判定しない) |
| | | upper_a<br />lower_a | X軸回転上限 |
| | | upper_b<br />lower_b | Y軸回転上限 |
| | | upper_c<br />lower_c | Z軸回転上限 |
| algor | |  | マッチングアルゴリズム(1:ICP その他は未定) |

**※3** master(選択されたモデルのパラメータ)

| Parameter(大項目) | Parameter(中項目)        | Parameter(小項目)    | 説明                                                         |
| ----------------- | ------------------------ | -------------------- | ------------------------------------------------------------ |
| recipe_id  |          |                | モデルのレシピID |
| cropper    |          |                | クロップパラメータ/cropperから取得する。 |
|            | zcrop    |                | Z方向クロップパラメータ |
|            |          | near           | Z方向クロップ位置（カメラ側） |
|            |          | far            | Z方向クロップ位置（床側） |
|            | sphere   |                | XY平面円クロップパラメータ  |
|            |          | x              | 中心X座標 |
|            |          | y              | 中心Y座標 |
|            |          | r              | 半径 |
|            | voxel    |                | voxelサイズ  |
|            | frame_id |                | 出力座標系  |
| ransac            |     |                            | ransacパラメータ       |
|             | fitness_threshold     |                            | ransacを終了するfitness閾値       |
|                   | max_iteration         |                                          | 反復の最大回数      |
|                   | max_validation        |                                    | 検証ステップの最大数     |
| icp               |     |  | ICPパラメータ     |
|                | fitness_threshold     |  | ICP一致率閾値（この値未満の場合にはICPの結果NGを返す）     |
|                   | translation_threshold |                                                        | ICP算出位置をロボットに通知する際の閾値<br />(組となっているupper,lowerが両方0の場合には閾値判定しない) |
|                   |                       | upper_x<br />lower_x | X座標上下限値 |
| | | upper_y<br />lower_y | Y座標上下限値 |
| | | upper_z<br />lower_z | Z座標上下限値 |
| | rotation_euler_threshold |  | ICP算出位置をロボットに通知する際の閾値(組となっているupper,lowerが両方0の場合には閾値判定しない) |
| | | upper_a<br />lower_a | X軸回転上限 |
| | | upper_b<br />lower_b | Y軸回転上限 |
| | | upper_c<br />lower_c | Z軸回転上限 |
| camera    |          |                | カメラパラメータ /rovi/pshift_genpc/cameraから取得する。 |
|            | exposure_time   |                | 露光時間  |
|            | gain   |                | ゲイン  |
| projector    |          |                | プロジェクターパラメータ /rovi/pshift_genpc/projectorから取得する。 |
|            | exposure_time   |                | 露光時間  |
|            | intencity   |                | 発光強度  |
|            | interval   |                | 発光間隔  |
| algor | |  | マッチングアルゴリズム(1:ICP その他は未定) |

**※4** frame_id(出力座標系 cropperで設定される)

カメラとワークの状態により4つの組み合わせがある。それぞれの合成点群の出力座標系については下記のように定める（出力座標系は、後段のFinderでの変換がなるべく小さくなるように定めているつもり）。

| #    | カメラ   | ワーク   | 出力座標系 |
| :--- | :------- | :------- | :--------- |
| 1    | 固定     | 固定     | カメラ     |
| 2    | ロボット | 固定     | カメラ     |
| 3    | 固定     | ロボット | ロボット   |
| 4    | ロボット | ロボット | ロボット   |
| 5    | 固定 | 固定 | ロボット   |
| 6    | ロボット | 固定 | ロボット   |

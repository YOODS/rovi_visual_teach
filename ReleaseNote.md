# ReleaseNote

## 2020.1.9

### rovi_utils

- ノイズ除去機能

|パラメータ|説明|パネル上の名称|パネル上の分類|対象プログラム|
|:----|:----|:----|:----|:----|
|/cropper/nfrad|ノイズを識別する球領域の半径|ノイズ識別半径|3.クロップ|cropper|
|/cropper/nfmin|球領域内の点がこの数以下の時ノイズとして除去する|ノイズ識別点数|3.クロップ|cropper|
|/searcher/normal_min_nn|法線決定領域内の点がこの数以下の時不良法線として除去する|不良法線識別点数|5.解析エンジン|searcher|

- 解析(認識)機能

|パラメータ|説明|パネル上の名称|パネル上の分類|対象プログラム|
|:----|:----|:----|:----|:----|
|/searcher/feature_mesh|特徴点のメッシュサイズ。法線メッシュより粗くすることで計算時間を短縮する|特徴点メッシュサイズ|5.解析エンジン|searcher|
|/searcher/rotate|回転対称物体の回対象数|回転対象数|5.解析エンジン|searcher|

- 廃止機能

|パラメータ|説明|パネル上の名称|パネル上の分類|対象プログラム|
|:----|:----|:----|:----|:----|
|/searcher/normal_max_nn|-|法線決定点数|5.解析エンジン|searcher|
|/searcher/feature_max_nn|-|特徴点決定点数|5.解析エンジン|searcher|

### rtk_tools

- UI機能変更
    - メッセージBOXがオープン状態で更新
    - 新しいメッセージから上位順に表示

### rovi_industrial

- Motoman対応

### rovi_master_teach  
- セットアップパネルの項目追加／削除
- パラメータ追加によるrecipe.d/*/param/yaml変更
~~~
cropper:
  cropR: 0
  cropZ: 0
  ladC: 0
  ladW: 100000
  mesh: 0.001
  nfmin: 0
  nfrad: 0
picker:
  azimuth:
    max: 1
    min: 0
  fitness:
    max: 1
    min: 0.7
  rmse:
    max: 5
    min: 0
rovi:
  live:
    camera:
      ExposureTime: 10000
      Gain: 0
  pshift_genpc:
    camera:
      ExposureTime: 8400
      Gain: 0
    projector:
      Intencity: 55
      Mode: 1
searcher:
  distance_threshold: 0.01
  feature_mesh: 0.002
  feature_radius: 0.015
  icp_threshold: 0.001
  normal_min_nn: 25
  normal_radius: 0.003
  rotate: 0  
~~~  
- すべてのrecipeに反映するには、
    - recipe.d下のひとつのparam.yamlを上記に合わせて編集  
    - rovi_master_teach下(roscd rovi_master_teach)で、recipe_mixer.pyを実行

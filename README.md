# Visual Teaching & Playback

## 準備  
以下をCheckoutしてBuildします。
- [rovi(コア)](https://github.com/YOODS/rovi)
- [rovi_utils(ユーティティ)](https://github.com/YOODS/rovi_utils)
- [rtk_tools(GUIツール)](https://github.com/YOODS/rtk_tools)

## 起動  
1. dashboardの起動  
弊社アプリケーションのエントリーポイントは全て**start.launch**です。
~~~
roslaunch rovi_master_teach start.launch
~~~
これによって先ずdashboardが起動されます。

2. アプリケーションの起動  
アプリケーションを構成するlaunch群は**dashboard**から起動されます。どのlaunchを起動するかはdashboard.yamlの設定に従います。
dashboard.yamlのlaunchプロパティ下のautoプロパティにて、dashboardが起動されてから当該launchが起動するまでの時間を設定します。autoプロパティが無いlaunchは自動起動されませんが、dashboardの**Start**ボタンにて手動で起動できます。

### dashboard.yamlの編集  
dashboard.yamlはdashboard.d以下のファイルへのシンボリックリンクになっています。機器構成に合わせてリンクを編集します。  
下はdashboard設定として*ur5_sxga.yaml*を使う場合の例です。
~~~
ln -fs dashboard.d/ur5_sxga.yaml dashboard.yaml
~~~
VT評価キットには*eval.yaml*を使います。以下に例示します。
~~~
ln -fs dashboard.d/eval.yaml dashboard.yaml
~~~
## スクリーンショット
![object](img/snap.png)

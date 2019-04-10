#!/usr/bin/env node

const ros = require('rosnodejs');
const geometry_msgs = ros.require('geometry_msgs').msg;
const sensor_msgs = ros.require('sensor_msgs').msg;
const std_msgs = ros.require('std_msgs').msg;
const rovi_msgs = ros.require('rovi').msg;
const EventEmitter = require('events').EventEmitter;
const Notifier = require('../rovi/script/notifier.js');
const net=require('net');

// 2019.02.20 Nomura start
const execSync = require('child_process').execSync;
// 2019.02.20 Nomura end

require('date-utils')

for (let i = 0; i < process.argv.length; i++) {
  console.log('argv['+i.toString()+'] = '+process.argv[i]);
}

// ロボット種別を読み込む
//const robotType = execSync('rosparam get /mt/robot_type').toString().replace(/\r?\n/g, '');
//console.log('robotType['+robotType+ ']');

const robotType=process.argv[2]
console.log('robotType='+robotType);


let masterType = ""; //レシピ番号（文字列も可）
let translationX_upper_threshold = 0.0;
let translationX_lower_threshold = 0.0;
let translationY_upper_threshold = 0.0;
let translationY_lower_threshold = 0.0;
let translationZ_upper_threshold = 0.0;
let translationZ_lower_threshold = 0.0;
let rotationEulerA_upper_threshold = 0.0;
let rotationEulerA_lower_threshold = 0.0;
let rotationEulerB_upper_threshold = 0.0;
let rotationEulerB_lower_threshold = 0.0;
let rotationEulerC_upper_threshold = 0.0;
let rotationEulerC_lower_threshold = 0.0;

let proc_message = "";
let error_code = "";
let matrix44 = new Array();


var rOrder = "abc"; //初期値はabcにしておく

if (robotType == "Mitsubishi") {
   rOrder = "cba";
} else if (robotType == "Fanuc") {
   rOrder = "abc";
}
console.log('rOrder='+rOrder);

// solverから受信したRT (float[]) を matrix44に変換する。
function floats2matrix44(rt){
  //rt to matrix44
  let cnt = 0;
  let matrix44 = new Array(4);
  matrix44 = new Array(4);
  for(let i=0; i<4; i++){
    matrix44[i] = new  Array(4);
    for(let j=0; j<4; j++){
      matrix44[i][j] = rt[cnt];
      //console.log('matrix44[' + i + '][' + j + ']:' + matrix44[i][j]);
      cnt++;
    }
  }
  return matrix44;
}

// 以下はpythonからjsで実施するように変更
// RTからtfへの変換(CBA)
function fromRTtoEulerCBA(matrix44){ // RobotRTToRxyzCBA
  let A=0.0;
  let B=0.0;
  let C=0.0;
  let Rx=0.0;
  let Ry=0.0;
  let Rz=0.0;
  let half_pi=Math.PI/2.0;
  let req_limit=1e-8;

  if (Math.abs(matrix44[2][0]+1)<=req_limit || Math.abs(matrix44[2][0]-1)<=req_limit){
    A=0;
    if (Math.abs(matrix44[2][0]-1)<=req_limit) B=-half_pi;
    if (Math.abs(matrix44[2][0]+1)<=req_limit) B=half_pi;
    C=Math.atan2(-matrix44[0][1],matrix44[1][1]);
  }else{
    B=Math.asin(-1*matrix44[2][0]);
    C=Math.atan2(matrix44[1][0],matrix44[0][0]);
    A=Math.atan2(matrix44[2][1],matrix44[2][2]);
  }
  Rx=matrix44[0][3];
  Ry=matrix44[1][3];
  Rz=matrix44[2][3];
  A_degree=A/Math.PI*180.0;
  B_degree=B/Math.PI*180.0;
  C_degree=C/Math.PI*180.0;

  //console.log('Rx:'+Rx+' Ry:'+Ry+' Rz:'+Rz+' A:'+A_degree+' B:'+B_degree+' C:'+C_degree);
  let vec=new Array();
  vec.push(Rx);
  vec.push(Ry);
  vec.push(Rz);
  vec.push(A_degree);
  vec.push(B_degree);
  vec.push(C_degree);
  vec.push(0);

  return vec
}

// RTからtfへの変換(ABC)
function fromRTtoEulerABC(matrix44){  // RobotRTToRxyzABC
  let A=0.0;
  let B=0.0;
  let C=0.0;
  let Rx=0.0;
  let Ry=0.0;
  let Rz=0.0;
  let half_pi=Math.PI/2.0;
  let req_limit=1e-8;

  if (Math.abs(matrix44[0][2]+1)<=req_limit || Math.abs(matrix44[0][2]-1)<=req_limit){
    A=0
    if (Math.abs(matrix44[0][2]-1)<=req_limit) B=half_pi;
    if (Math.abs(matrix44[0,2]+1)<=req_limit) B=-half_pi;
    C=Math.atan2(matrix44[1,0],matrix44[1,1]);
  }else{
    B=Math.asin(matrix44[0][2]);
    C=Math.atan2(-matrix44[0][1], matrix44[0][0]);
    A=Math.atan2(-matrix44[1][2], matrix44[2][2]);
  }
  Rx=matrix44[0][3];
  Ry=matrix44[1][3];
  Rz=matrix44[2][3];
  A_degree=A/Math.PI*180.0;
  B_degree=B/Math.PI*180.0;
  C_degree=C/Math.PI*180.0;

  //console.log('Rx:'+Rx+' Ry:'+Ry+' Rz:'+Rz+' A:'+A_degree+' B:'+B_degree+' C:'+C_degree);
  let vec=new Array();
  vec.push(Rx);
  vec.push(Ry);
  vec.push(Rz);
  vec.push(A_degree);
  vec.push(B_degree);
  vec.push(C_degree);
  vec.push(0);

  return vec
}

// 指定されたマスターのパラメータをrosparamで取得する。（存在しない場合には指定されたデフォルト値を返す）
function getRosparam(key,default_value) {
  ret = default_value;

  try {
    cmdstr = 'rosparam get /mt/master/icp/' + key;
    //console.log('##### cmdstr[' + cmdstr + ']');
    ret = execSync(cmdstr).toString().replace(/\r?\n/g, '');
  }catch(e){}

  console.log('###### ' + key + '[' + ret + ']');

  return ret;
}

// 指定されたレシピIDをrosparam /mt/recipe にセットする。
function selectRecipe(value) {
  ret = true;
  try {
    cmdstr = 'rosparam set /mt/recipe ' + value;
    console.log('##### cmdstr[' + cmdstr + ']');
    execSync(cmdstr).toString().replace(/\r?\n/g, '');
  }catch(e){
    ret = false;
  }

  console.log('###### selectRecipe ret='  + ret);

  return ret;
}

// 閾値でロボットに移動位置を通知するかを判断する。
function checkPosition(tfeuler) {
  // upper,lowerの両方が0の場合には閾値判定を行わない
  let isNG = false;
  if( parseFloat(translationX_upper_threshold) != 0 || parseFloat(translationX_lower_threshold) != 0 ){
    if( parseFloat(translationX_upper_threshold) < parseFloat(tfeuler[0].toFixed(3)) || parseFloat(translationX_lower_threshold) > parseFloat(tfeuler[0].toFixed(3)) ){
      console.log('###### ERROR translation X');
      return false;
    }
  }
  if( parseFloat(translationY_upper_threshold) != 0 || parseFloat(translationY_lower_threshold) != 0 ){
    if( parseFloat(translationY_upper_threshold) < parseFloat(tfeuler[1].toFixed(3)) || parseFloat(translationY_lower_threshold) > parseFloat(tfeuler[1].toFixed(3)) ){
      console.log('###### ERROR translation Y');
      return false;
    }
  }
  if( parseFloat(translationZ_upper_threshold) != 0 || parseFloat(translationZ_lower_threshold) != 0 ){
    if( parseFloat(translationZ_upper_threshold) < parseFloat(tfeuler[2].toFixed(3)) || parseFloat(translationZ_lower_threshold) > parseFloat(tfeuler[2].toFixed(3)) ){
      console.log('###### ERROR translation Z');
      return false;
    }
  }
  if( parseFloat(rotationEulerA_upper_threshold) != 0 || parseFloat(rotationEulerA_lower_threshold) != 0 ){
    if( parseFloat(rotationEulerA_upper_threshold) < parseFloat(tfeuler[3].toFixed(3)) || parseFloat(rotationEulerA_lower_threshold) > parseFloat(tfeuler[3].toFixed(3)) ){
      console.log('###### ERROR rotationEuler A');
      return false;
    }
  }
  if( parseFloat(rotationEulerB_upper_threshold) != 0 || parseFloat(rotationEulerB_lower_threshold) != 0 ){
    if( parseFloat(rotationEulerB_upper_threshold) < parseFloat(tfeuler[4].toFixed(3)) || parseFloat(rotationEulerB_lower_threshold) > parseFloat(tfeuler[4].toFixed(3)) ){
      console.log('###### ERROR rotationEuler B');
      return false;
    }
  }
  if( parseFloat(rotationEulerC_upper_threshold) != 0 || parseFloat(rotationEulerC_lower_threshold) != 0 ){
    if( parseFloat(rotationEulerC_upper_threshold) < parseFloat(tfeuler[5].toFixed(3)) || parseFloat(rotationEulerC_lower_threshold) > parseFloat(tfeuler[5].toFixed(3)) ){
      console.log('###### ERROR rotationEuler C');
      return false;
    }
  }
  return true;
}

function toCoords(data) {
// data format is '***(X,Y,Z,A,B,C)***\n'.
  const str = data.toString();
  const ary = str.replace(/\).*/g, ']').replace(/.*\(/, '[').replace(/E\+/g, 'E').replace(/\+/g, '');
//  console.log('ary={' + ary + '}');
  let coords = [];
  try {
    coords = JSON.parse('[' + ary + ']');
  }
  catch(e) {
    console.log("error " + e);
  }
  console.log('coord='+coords.toString());
  let euler=new geometry_msgs.Transform();
  euler.translation.x=coords[0][0];
  euler.translation.y=coords[0][1];
  euler.translation.z=coords[0][2];
  euler.rotation.x=coords[0][3];
  euler.rotation.y=coords[0][4];
  euler.rotation.z=coords[0][5];
  euler.rotation.w=1;
//  console.log(JSON.stringify(euler));
  return euler
}

function xyz2quat(e) {
  let tf=Object.assign({},e);
  let k = Math.PI / 180 * 0.5;
  let cx = Math.cos(e.rotation.x * k);
  let cy = Math.cos(e.rotation.y * k);
  let cz = Math.cos(e.rotation.z * k);
  let sx = Math.sin(e.rotation.x * k);
  let sy = Math.sin(e.rotation.y * k);
  let sz = Math.sin(e.rotation.z * k);
  if (rOrder=="cba") {
    tf.rotation.x = cy * cz * sx - cx * sy * sz;
    tf.rotation.y = cy * sx * sz + cx * cz * sy;
    tf.rotation.z = cx * cy * sz - cz * sx * sy;
    tf.rotation.w = sx * sy * sz + cx * cy * cz;
  } else {
    tf.rotation.x = sx * cy * cz - cx * sy * sz;
    tf.rotation.y = cx * sy * cz + sx * cy * sz;
    tf.rotation.z = cx * cy * sz - sx * sy * cz;
    tf.rotation.w = cx * cy * cz + sx * sy * sz;
  }
  return tf;
}

setImmediate(async function(){
  const event=new EventEmitter();
  const rosNode=await ros.initNode('socket');
//Subscribers
  // masterteachからのRT
  rosNode.subscribe('/robot/result_rt', rovi_msgs.Floats, async function(rt) {
    let now = new Date();
    // float[] to matrix44
    console.log('##### receive result_rt ' +now.toFormat('YYYY_MM_DD_HH24MISS'));
    matrix44 = floats2matrix44(rt.data);
    console.log('##### result_rt matrix44=' +matrix44);
  });
  // masterteachからの処理結果コード
  rosNode.subscribe('/solver/error', std_msgs.String, async function(str) {
    let now = new Date();
    console.log('##### receive error ' +now.toFormat('YYYY_MM_DD_HH24MISS'));
    error_code = str.data;
    console.log('##### solver_error error_code=' +error_code);
  });
  // masterteachからの処理結果メッセージ
  rosNode.subscribe('/solver/message', std_msgs.String, async function(str) {
    let now = new Date();
    console.log('##### receive message ' +now.toFormat('YYYY_MM_DD_HH24MISS'));
    proc_message = str.data;
    console.log('##### solver_message message=' +proc_message);

  });
  rosNode.subscribe('/robot/Y1',std_msgs.Bool,async function(ret) {
    let now = new Date();
    console.log('##### receive Y1 --> emit caught' +now.toFormat('YYYY_MM_DD_HH24MISS'));
    event.emit('caught',ret.data);
  });
  rosNode.subscribe('/robot/Y2', std_msgs.Bool, async function(ret) {
    let now = new Date();
    console.log('##### receive Y2 -> emit solved ' +now.toFormat('YYYY_MM_DD_HH24MISS'));
    event.emit('solved', ret.data);
  });
  rosNode.subscribe('/solver/mTs',geometry_msgs.Transform,async function(tf) {
    let now = new Date();
    console.log('##### receive mTs --> emit position ' +now.toFormat('YYYY_MM_DD_HH24MISS'));
    event.emit('position',tf);
  });
  //RECIPE
  rosNode.subscribe('/robot/Y3',std_msgs.Bool,async function(ret) {
    let now = new Date();
    console.log('##### receive Y3 --> emit caught' +now.toFormat('YYYY_MM_DD_HH24MISS'));
    event.emit('change_master',ret.data);
  });

//Publisher
  const pub_tf=rosNode.advertise('/robot/tf', geometry_msgs.Transform);
  const pub_solX0=rosNode.advertise('/robot/X0', std_msgs.Bool);	// Clear
  const pub_solX1=rosNode.advertise('/robot/X1', std_msgs.Bool);	// Capture
  const pub_solX2=rosNode.advertise('/robot/X2', std_msgs.Bool);	// Calc
  const pub_solX3=rosNode.advertise('/robot/X3', std_msgs.Bool);	// RECIPE
  const pub_sol_reset=rosNode.advertise('/robot/reset', std_msgs.Bool);	// error_code及びmessageのリセット
  const pub_gridX0=rosNode.advertise('/gridboard/X0', std_msgs.Bool);
  const pub_gridImg=rosNode.advertise('/gridboard/image_in', sensor_msgs.Image);

//Parameter notifier
  const param=new Notifier(rosNode,'/gridboard');
  param.on('change',function(key,val){
    console.log('param '+key+'='+val);
    pub_gridX0.publish(new std_msgs.Bool());
  });
  setTimeout(function(){ param.start(); },1000);

//Socket
  let cnt=0;
  const server = net.createServer(function(conn){
    console.log('r_socket connected');
    conn.setTimeout(60000); //60秒

    let msg='';
    conn.on('data', function(data){
      msg+=data.toString();
      console.log('msg='+msg);
      if(msg.indexOf('(')*msg.indexOf(')')<0) return;

      if(msg.startsWith('P1')){
        //publish /robot/tf, no reply
        let tf=toCoords(msg);
        let qt=xyz2quat(tf);

        //reset
        pub_sol_reset.publish(new std_msgs.Bool());

        pub_tf.publish(qt);
      }
      else if(msg.startsWith('X0')){
        //publish /solver/X0

        //reset
        pub_sol_reset.publish(new std_msgs.Bool());

        pub_solX0.publish(new std_msgs.Bool());
        conn.write('OK\n');
        cnt=0;
      }
      else if(msg.startsWith('X1')){
        let now = new Date();
	console.log('##### call_X1 ' +now.toFormat('YYYY_MM_DD_HH24MISS'));

        //reset
        pub_sol_reset.publish(new std_msgs.Bool());

        //publish /robot/tf
        let euler=toCoords(msg);
        let qt=xyz2quat(euler);

        pub_tf.publish(qt);
        event.once('position',function(tf){
          console.log('['+cnt.toString()+']position');
          //publish /solver/X1
          pub_solX1.publish(new std_msgs.Bool());
        });

        // 処理終了
        event.once('caught',function(ret){  // send capture result
          now = new Date();
	  console.log('##### caught start ' +now.toFormat('YYYY_MM_DD_HH24MISS'));

          console.log('['+cnt.toString()+']caught: '+((ret) ? 'OK' : 'NG'));
          if (parseInt(error_code) == 0) {
            conn.write('OK\n');
            cnt+=1;
          } else {
            conn.write('NG\n');
            //conn.write('999');
            conn.write(error_code);
          }
          console.log('[2]sent!\x0d');
        });
      }
      else if(msg.startsWith('X2')){
        //publish /solver/X2
        let now = new Date();

	console.log('##### get rosparam ' +now.toFormat('YYYY_MM_DD_HH24MISS'));

        // rosparamから移動位置の閾値を取得する
        translationX_upper_threshold = getRosparam('translation_threshold/upper_x',0.0);
        translationX_lower_threshold = getRosparam('translation_threshold/lower_x',0.0);
        translationY_upper_threshold = getRosparam('translation_threshold/upper_y',0.0);
        translationY_lower_threshold = getRosparam('translation_threshold/lower_y',0.0);
        translationZ_upper_threshold = getRosparam('translation_threshold/upper_z',0.0);
        translationZ_lower_threshold = getRosparam('translation_threshold/lower_z',0.0);
        rotationEulerA_upper_threshold = getRosparam('rotation_euler_threshold/upper_a',0.0);
        rotationEulerA_lower_threshold = getRosparam('rotation_euler_threshold/lower_a',0.0);
        rotationEulerB_upper_threshold = getRosparam('rotation_euler_threshold/upper_b',0.0);
        rotationEulerB_lower_threshold = getRosparam('rotation_euler_threshold/lower_b',0.0);
        rotationEulerC_upper_threshold = getRosparam('rotation_euler_threshold/upper_c',0.0);
        rotationEulerC_lower_threshold = getRosparam('rotation_euler_threshold/lower_c',0.0);

	console.log('##### call_X2 ' +now.toFormat('YYYY_MM_DD_HH24MISS'));

        //reset
        pub_sol_reset.publish(new std_msgs.Bool());

        // masterteachの実行
        pub_solX2.publish(new std_msgs.Bool());

        // 処理終了
        // ICP終了通知受信
        event.once('solved', function(ret) {   //reply picking pose to robot controller
          now = new Date();
	  console.log('##### solved start ' +now.toFormat('YYYY_MM_DD_HH24MISS'));

          // ロボット種別ごとの処理
	  if (rOrder=="cba") { // Mitsubishi
            if (parseInt(error_code) == 0) {
              //console.log('##### solved matrix44=' +matrix44);
	      tfeuler=fromRTtoEulerCBA(matrix44).slice();

              if(robotType == "Mitsubishi"){       // Mitsubishi （Mitsubishi以外もcbaの場合があるのか？）
                //ここで、角度の変換が必要かも・・
                //ロボットは 0 <-- 180,180 --> 0 で、
                //ICPが、
                // 1.  180 <-- 0 --> 180
                // 2. -180 <-- 0 --> 180
                // で返す場合には、roll,pitch,yawを変換する必要がある。
                // 1.
                //tfeuler[3] = 180.0 - tfeuler[3]
                //tfeuler[4] = 180.0 - tfeuler[4]
                //tfeuler[5] = 180.0 - tfeuler[5] 
                // 2.
                //tfeuler[3] = -180.0 - tfeuler[3]
                //tfeuler[4] = -180.0 - tfeuler[4]
                //tfeuler[5] = -180.0 - tfeuler[5]

               if (tfeuler[3]<0){
	          -1 * 180-(tfeuler[3]-(tfeuler[3]/360)*360); 
                }else{
                  1 * 180-(tfeuler[3]-(tfeuler[3]/360)*360);
      	        }
	        if (tfeuler[4]<0){
	          -1 * 180-(tfeuler[4]-(tfeuler[4]/360)*360);
                }else{
                  1 * 180-(tfeuler[4]-(tfeuler[4]/360)*360);
                }
	        if (tfeuler[5]<0){
                  -1 * 180-(tfeuler[5]-(tfeuler[5]/360)*360);
                }else{
                  1 * 180-(tfeuler[5]-(tfeuler[5]/360)*360);
                }
              }

              // rosparamで移動位置の閾値を取得し、超過していない場合はOKを、超過した場合はNGを返す
              if(checkPosition(tfeuler) == true){
                okstr = 'OK\x0d(' + tfeuler[0].toFixed(3) + ',' + tfeuler[1].toFixed(3) + ',' + tfeuler[2].toFixed(3) + ',' + tfeuler[3].toFixed(3) + ',' + tfeuler[4].toFixed(3) + ',' + tfeuler[5].toFixed(3) + ')(7,0)\x0d';
                console.log(okstr);
                conn.write(okstr);
              }else{
                console.log('[2]send robot NG...\x0d');
                conn.write('NG\x0d');
              }
              // 2019.03.07 Nomura end
            }
            else {
              console.log('[2]send robot NG...\x0d');
              conn.write('NG\x0d');
            }
            console.log('[2]sent!\x0d');
          }else{  // Fanuc
            if (parseInt(error_code) == 0) {
              //console.log('##### solved matrix44=' +matrix44);
              tfeuler=fromRTtoEulerABC(matrix44).slice();

              // rosparamで移動位置の閾値を取得し、超過していない場合はOKを、超過した場合はNGを返す
              if(checkPosition(tfeuler) == true){
                conn.write('OK\n');
                let tstr="'"+tfeuler[0].toFixed(3)+"''"+tfeuler[1].toFixed(3)+"''"+tfeuler[2].toFixed(3)+"'";
                let rstr="'"+tfeuler[3].toFixed(3)+"''"+tfeuler[4].toFixed(3)+"''"+tfeuler[5].toFixed(3)+"'";
                console.log('translation '+tstr);
                console.log('rotation '+rstr);
                conn.write(tstr+rstr);
              }else{
                conn.write('NG\n');
                //conn.write('999');
                conn.write(error_code);
              }
            } else {
              conn.write('NG\n');
              //conn.write('999');
              conn.write(error_code);
            }
            console.log('[2]sent!\x0d');
          }
        });
      }
      else if(msg.startsWith('X3')){ //RECIPE
        let now = new Date();
	console.log('##### call_X3 ' +now.toFormat('YYYY_MM_DD_HH24MISS'));

        let X3_msg=new std_msgs.String();

	const str = msg.toString();
  	let ary = String(str.replace(/\).*/g, '').replace(/.*\(/, '')).replace(/\+/g, '').replace(/\r?\n/g, '').replace(/\"/g, '');
  	X3_msg.data = ary;

	console.log('##### chage_master X3_msg[' + X3_msg.data.toString() + ']');

        // rosparam に指定されたrecipe_idをセットする。
        ret = selectRecipe(X3_msg.data.toString());

        if(ret){
          //reset
          pub_sol_reset.publish(new std_msgs.Bool());

          //publish /solver/X3
          //pub_solX3.publish(X3_msg);
          pub_solX3.publish(new std_msgs.Bool());

          // 処理終了
          event.once('change_master',function(ret){  // send X3 result
            now = new Date();
	    console.log('##### chage_master start ' +now.toFormat('YYYY_MM_DD_HH24MISS'));

            console.log('['+cnt.toString()+']change_master: '+((ret) ? 'OK' : 'NG'));
            if (parseInt(error_code) == 0) {
              conn.write('OK\n');
              cnt+=1;
            } else {
              conn.write('NG\n');
              //conn.write('999');
              conn.write(error_code);
            }
          });
        } else {
          conn.write('NG\n');
          //conn.write('999');
          conn.write(error_code);
        }
        console.log('[2]sent!\x0d');
      }
      msg='';
      return;
    });
    conn.on('close', function(){
      console.log('connection closed');
    });
    conn.on('timeout',function(){
      event.removeAllListeners();
      conn.write('NG\n'+"'408'"); //Request timeout
      console.log('request timeout');
      conn.destroy();
    });
  }).listen(3000);

//Subscriber (should be done after Looping started)
  setTimeout(function(){
    rosNode.subscribe('/rovi/left/image_rect', sensor_msgs.Image, async function(img){
      event.emit('image',img);
    });
    rosNode.subscribe('/gridboard/done', std_msgs.Bool, async function(f){
      event.emit('grid',f);
    });
  },1000);

//Looping image->grid
  while(true){
    await Promise.all([
      new Promise(function(resolve){
        event.once('image',function(img){
          pub_gridImg.publish(img);
          resolve(true);
        });
      }),
      new Promise(function(resolve){
        event.once('grid',async function(f){
          resolve(true);
        });
      })
    ]);
  }
});

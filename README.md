# Comfyui-task-notify-timer-watchdog-optional-email-sending
安装方法：
全部放入COMFYUI
<br><br><br>
任务成功、失败提醒不需要放置节点，自动运行  
成功提示音在当前列表所有任务完成后才会触发  
需要更换提示音、加入邮箱提醒，进入notify.py填写数据  （成功没有邮箱提醒）
  <br><br><br>
comfyui崩溃提醒  
需要用独立窗口启动watchdog.bat，想自动一点就用自己的方法让它和comfyui一块启动，我自用的是文件中的launch_comfyui.bat  
逻辑：启动后持续检测是否能连接到127.0.0.1:8188，连接成功后开始检测127.0.0.1:8188是否断开，断开则触发提醒，提醒一次后持续检测能否连接网址并循环  
所以正常退出comfyui前先关闭watchdog，不然会触发提醒，同时关闭也行，别间隔太久  
需要更换提示音、加入邮箱提醒，进入watchdog.bat填写数据  
<br><br>

任务计时器  
  
输出格式为  
"xxxx年xx月xx日xx:xx:xx - task_filename  
耗时：xx时xx分xx秒"的字符串内容（时间为任务开始时间）  
  
timer record节点：  
需要两个  
两个trigger分别连接任务开始和结束经过的节点  
time_recorder连接到timer out节点的start_time和end_time  
！！这两个节点的输出都要额外接一个预览，不然会出bug导致耗时显示为0！！  
  
timer output节点:  
start_time连接到开始时间的timer record节点  
end_time连接到结束时间的timer record节点
task_filename为字符串中需要显示文件名，不填则为空
log_filename为保存文件的名字，需要是txt格式，会在文件的下一行写入字符串信息，不填则不保存至文件
<br><br><br>
全部由ai制作，真的这种基础功能我从没想过得现造，类似功能插件老是莫名失效，要不就是麻烦。鉴于我应该不会更新，就不研究怎么匹配git链接安装了

<template>
  		<div class="module">
			<!-- 左边模块 -->
			<div class="module_left">
				<!-- 标题 -->
				<div class="module_label">
					<div class="module_lable_item"></div>
					<div class="module_lable_item_content" data-i18n="Video Settings">视频设置</div>
				</div>
				<!-- 内容 -->
				<div class="module_content">
					<h1 class="module_left_configItem_lable" data-i18n="Language">语言</h1>
					<select class="module_left_configItem_select" id="languageType" @change="onSelectLanguageType()">
						<option value="zh-CN">中文</option>
						<option value="en">English</option>
					</select>
					<br>

					<h1 class="module_left_configItem_lable" data-i18n="Play mode">播放模式</h1>
					<select class="module_left_configItem_select" id="streamType" @change="onSelectStreamType()">
						<option value="realplay" data-i18n="Preview">直播</option>
						<option value="playback" data-i18n="Playback">回放</option>
					</select>
					<br>

					<h1 class="module_left_configItem_lable" data-i18n="Video format">视频格式 </h1>
					<select class="module_left_configItem_select" id="protocol" @change="onSelectProtocol()">
						<option value="httpFlv" data-decoder="decoderMSE decoderWasm" data-speed="1.0">FLV</option>
						<option value="http-wsFlv" data-decoder="decoderMSE" class="previewModule">WS-FLV</option>
						<option value="httpHls" data-decoder="decoderMSE decoderWasm">HLS</option>
						<option value="WS" data-decoder="decoderWasm" class="previewModule">WS-PRI</option>
						<option value="WebRTC" data-decoder="decoderMSE webRTCTalkModule talkModule" class="previewModule">WebRTC</option>
						<option value="mp4" data-decoder="decoderMSE mp4PlaybackModule" data-speed="1.0" class="playbackModule">MP4</option>
						<option value="pri" data-decoder="decoderWasm devicePreviewModule devicePlaybackModule talkModule" data-speed-disabled="4.0">PRI(Device)</option>
					</select>
					<br>
					<!--PRI(Device) change  -->
					<h1 class="module_left_configItem_lable devicePreviewModule">
						<span data-i18n="Mode">模式</span>
					</h1>
					<select class="module_left_configItem_select devicePreviewModule" id="priConfigModule" @change="onSelectPRI_Module('preview')">
						<option value="url" data-decoder="devicePreviewModule_children_url" data-i18n="Video address">视频地址</option>
						<option value="info" data-decoder="devicePreviewModule_children_info" data-i18n="Device Information">设备信息</option>
					</select>
					<br class="devicePreviewModule">
					<h1 class="module_left_configItem_lable devicePlaybackModule">
						<span data-i18n="Mode">模式</span>
					</h1>
					<select class="module_left_configItem_select devicePlaybackModule" id="priConfigModule_local" @change="onSelectPRI_Module('playback')">
						<option value="url" data-decoder="devicePlaybackModule_children_url" data-i18n="Video address">视频地址</option>
						<option value="local" data-decoder="devicePlaybackModule_children_info" data-i18n="Local file">本地文件</option>
					</select>
					<br class="devicePlaybackModule">

					<!-- MP4 change -->
					<h1 class="module_left_configItem_lable mp4PlaybackModule">
						<span data-i18n="Mode">模式</span>
					</h1>
					<select class="module_left_configItem_select mp4PlaybackModule" id="mp4ConfigModule" @change="onSelectMP4_Module()">
						<option value="url" data-decoder="mp4PlaybackModule_children_url" data-i18n="Video address">视频地址</option>
						<option value="local" data-decoder="mp4PlaybackModule_children_info" data-i18n="Local file">本地文件</option>
					</select>
					<br class="mp4PlaybackModule">

					<!-- webRTC change-->
					<h1 class="module_left_configItem_lable webRTCTalkModule">
						<span data-i18n="Mode">对讲模式</span>
					</h1>
					<select class="module_left_configItem_select webRTCTalkModule" id="webRTCTalkType" @change="onSelectWebRTCTalk_Module()">
						<option value="one-way-video" data-decoder="webRTCTalkModule_children_oneTalk" data-i18n="Unidirectional">单向</option>
					</select>
					<br class="webRTCTalkModule">



					<h1 class="module_left_configItem_lable devicePreviewModule_children_url mp4PlaybackModule_children_url devicePlaybackModule_children_url" data-i18n="Video address">视频地址 </h1>
					<textarea class="module_left_configItem_textarea devicePreviewModule_children_url mp4PlaybackModule_children_url devicePlaybackModule_children_url" rows="12" id="inputUrl"></textarea>
					<br class="devicePreviewModule_children_url mp4PlaybackModule_children_url devicePlaybackModule_children_url">



					<!-- PRI(Device) config-->
					<h1 class="module_left_configItem_lable devicePreviewModule_children_info">
						<span data-i18n="Device Information - IP (Local Area Network)">设备信息—IP(局域网)</span>
						<span style="cursor: default;" data-i18n-title="To obtain Salt, please provide complete device information." title="获取Salt，请填写完整设备信息">ℹ️</span>
					</h1>
					<input class="module_left_configItem_input devicePreviewModule_children_info" type="text" id="deviceIP" value="" />
					<br class="devicePreviewModule_children_info">
					<h1 class="module_left_configItem_lable devicePreviewModule_children_info">
						<span data-i18n="Device Information - Port (Local Area Network)">设备信息—端口(局域网)</span>
					</h1>
					<input class="module_left_configItem_input devicePreviewModule_children_info" type="text" id="devicePort" value="" />
					<br class="devicePreviewModule_children_info">
					<h1 class="module_left_configItem_lable devicePreviewModule_children_info">
						<span data-i18n="Device Information - Account">设备信息—账号</span>
					</h1>
					<input class="module_left_configItem_input devicePreviewModule_children_info" type="text" id="deviceUsername" value="" />
					<br class="devicePreviewModule_children_info">
					<h1 class="module_left_configItem_lable devicePreviewModule_children_info">
						<span data-i18n="Device Information - Password">设备信息—密码</span>
					</h1>
					<input class="module_left_configItem_input devicePreviewModule_children_info" type="text" id="devicePassword" value="" />
					<br class="devicePreviewModule_children_info">
					<h1 class="module_left_configItem_lable devicePreviewModule_children_info">
						<span data-i18n="Device Information - Password">设备信息—通道序号</span>
						<span style="cursor: default;" data-i18n-title="The channel number of the IPC device is 0. The sequence numbers for the multi-channel devices of DVR and NVR start from 0." title="IPC设备通道序号是0，DVR、NVR多通道设备的序号起始是0">ℹ️</span>
					</h1>
					<input class="module_left_configItem_input devicePreviewModule_children_info" type="text" pattern="\d*" oninput="this.value=this.value.replace(/[^0-9]/g,'')" id="deviceChannel" value="" />
					<br class="devicePreviewModule_children_info">
					<h1 class="module_left_configItem_lable devicePreviewModule_children_info">
						<span data-i18n="Device Information - Password">设备信息—码流类型</span>
					</h1>
					<select class="module_left_configItem_select devicePreviewModule_children_info" id="deviceStream" @change="onSelectDeviceStream()">
						<option value="Main" data-i18n="Main stream">主码流</option>
						<option value="Sub" data-i18n="Sub stream">辅码流</option>
					</select>
					<br class="devicePreviewModule_children_info">
					<!-- MP4、devicePRI Local -->
					<h1 class="module_left_configItem_lable mp4PlaybackModule_children_info devicePlaybackModule_children_info">
						<span data-i18n="Local file">本地文件</span>
					</h1>
					<input class="module_left_configItem_input mp4PlaybackModule_children_info devicePlaybackModule_children_info" type="file" id="fileSelector" />
					<br class="mp4PlaybackModule_children_info devicePlaybackModule_children_info">
					<!-- webRTC -->
					<h1 class="module_left_configItem_lable webRTCTalkModule_children_oneTalk">
						<span data-i18n="Single-way talk address">单向对讲地址</span>
					</h1>
					<textarea class="module_left_configItem_textarea webRTCTalkModule_children_oneTalk" rows="6" id="webRTCTalkUrl"></textarea>
					<br class="webRTCTalkModule_children_oneTalk">
					<h1 class="module_left_configItem_lable webRTCTalkModule_children_twoTalk">
						<span data-i18n="Double-way talk local video">双向视频本地视频</span>
					</h1>
					<!--webRTC 双向对讲 本地视频 -->
					<video id="localVideo" class="module_left_configItem_textarea webRTCTalkModule_children_twoTalk" autoplay poster="/jfplayer/web/img/logo2.png" controlslist="nodownload" crossorigin="anonymous" style="z-index: 1;background-color: #000;">
						Your browser is too old which doesn't support HTML5 video.
					</video>
					<br class="webRTCTalkModule_children_twoTalk">

					<h1 class="module_left_configItem_lable playbackModule" data-i18n="Playback speed">播放速率</h1>
					<select class="module_left_configItem_select playbackModule" id="speed" @change="onSelectSpeed()">
						<option value=1.0 class="speedOpt speed1.0">x1.0</option>
						<option value=0.5 class="speedOpt speed0.5">x0.5</option>
						<option value=1.5 class="speedOpt speed1.5">x1.5</option>
						<option value=2.0 class="speedOpt speed2.0">x2.0</option>
            			<option value=3.0 class="speedOpt speed3.0">x3.0</option>
						<option value=4.0 class="speedOpt speed4.0">x4.0</option>
					</select>
					<br class="playbackModule">
					<h1 class="module_left_configItem_lable playbackModule">
						<span data-i18n="Fast-forward interval (ms)">快进/后退间隔（单位：ms)</span>
						<span style="cursor: default;" data-i18n-title="Range of values (3000 - 30000)" title="建议取值范围（10000 ~ 30000）">ℹ️</span>
					</h1>
					<input class="module_left_configItem_input playbackModule" type="text" pattern="\d*" oninput="this.value=this.value.replace(/[^0-9]/g,'')" id="fastForwardInterval" value="10000" />
					<br class="playbackModule">

					<h1 class="module_left_configItem_lable" data-i18n="Decode mode">解码模式</h1>
					<select class="module_left_configItem_select" id="decodingType" @change="onSelectDecoder()">
						<option value="0" class="decoderModule decoderWasm" data-i18n="Soft solution">软解</option>
						<option value="1" class="decoderModule decoderMSE" data-i18n="Hard solution">硬解</option>
						<option value="-1" data-i18n="Auto">自动</option>
					</select>
					<br>

					<h1 class="module_left_configItem_lable previewModule">
						<span data-i18n="Buffer duration (ms)">缓冲时长（单位：ms)</span>
						<span style="cursor: default;" data-i18n-title="Range of values (50 - 60,000)" title="取值范围（50 ~ 60000）">ℹ️</span>
					</h1>
					<input class="module_left_configItem_input previewModule" type="text" pattern="\d*" oninput="this.value=this.value.replace(/[^0-9]/g,'')" id="bufferTime" value="2000" />
					<br class="previewModule">

					<h1 class="module_left_configItem_lable previewModule" data-i18n="Preview frame-by-frame">预览追帧</h1>
					<select class="module_left_configItem_select previewModule" id="lastFrame">
						<option value="true" data-i18n="Open" selected>开启</option>
						<option value="false" data-i18n="Close">关闭</option>
					</select>
					<br class="previewModule">

					<h1 class="module_left_configItem_lable previewModule" data-i18n="Preview reconnection">预览重连</h1>
					<select class="module_left_configItem_select previewModule" id="previewReconn" @change="onSelectReconnType()">
						<option value="true" data-i18n="Open">开启</option>
						<option value="false" data-i18n="Close" selected>关闭</option>
					</select>
					<br class="previewModule">

					<h1 class="module_left_configItem_lable reconnectModule" style="display: none;">
						<span data-i18n="Reconn time(-1: unlimited)">重连次数(-1:无限制)</span>
						<span style="cursor: default;" data-i18n-title="Range of values (greater than 0)" title="取值范围（大于0）">ℹ️</span>
					</h1>
					<input class="module_left_configItem_input  reconnectModule" style="display: none;" type="text" pattern="\d*" id="reconnNumber" value="-1" />
					<br class=" reconnectModule" style="display: none;">

					<h1 class="module_left_configItem_lable reconnectModule" style="display: none;">
						<span data-i18n="Reconnect interval (ms)">重连间隔（单位：ms）</span>
						<span style="cursor: default;" data-i18n-title="Range of values (greater than 1000)" title="取值范围（大于1000）">ℹ️</span>
					</h1>
					<input class="module_left_configItem_input  reconnectModule" style="display: none;" type="text" pattern="\d*" oninput="this.value=this.value.replace(/[^0-9]/g,'')" id="reconnInterval" value="5000" />
					<br class=" reconnectModule" style="display: none;">

					<h1 class="module_left_configItem_lable playbackModule" data-i18n="Replay and re-broadcast">回放重播</h1>
					<select class="module_left_configItem_select playbackModule" id="playbackReplay">
						<option value="true" data-i18n="Open">开启</option>
						<option value="false" data-i18n="Close" selected>关闭</option>
					</select>
					<br class="playbackModule">

					<h1 class="module_left_configItem_lable" data-i18n="Log level">日志等级</h1>
					<select class="module_left_configItem_select" id="logLevel" @change="onSelectLogType(this)">
						<option value="0" data-i18n="Error">错误</option>
						<option value="10" data-i18n="Warn">警告</option>
						<option value="20" data-i18n="Info" selected>信息</option>
						<option value="30" data-i18n="Debug">调试</option>
						<option value="40" data-i18n="All">全部</option>
					</select>
					<br>

					<!-- footer -->
					<br>
					<br>
				</div>
			</div>
			<!-- 中间模块 -->
			<div class="module_middle">
				<div class="canvasDiv"  @dblclick="toggleFullscreen()">
					<div class="loadEffect" id="loading" style="display:none;">
						<span></span>
						<span></span>
						<span></span>
						<span></span>
						<span></span>
						<span></span>
						<span></span>
						<span></span>
					</div>
					<!-- 其他用途（数字放大） -->
					<canvas id="playCanvas" width="1152" height="644"></canvas>
				</div>

				<div class="gwmModule">
					<div class="canvasDiv1" @dblclick="toggleFullscreen()">
						<!-- 软解画板 -->
						<canvas id="playCanvas1" width="1152" height="644"></canvas>
					</div>
				</div>

				<div class="flvModule" style="display: none;">
					<video name="videoElement" class="centeredVideo" autoplay poster="/jfplayer/web/img/logo2.png" controlslist="nodownload" crossorigin="anonymous" width="1152" height="644" style="z-index: 1; " @dblclick="toggleFullscreen()">
						Your browser is too old which doesn't support HTML5 video.
					</video>
				</div>

				<!-- 控制菜单 -->
				<div id="canvasFoot" class="sideBar" style="z-index: 999;">
					<div class="footBar playbackModule">
						<div id="progressBar_div" style="display: none;">
							<span class="no-padding" style="width: 100%;">
								<span style="display: inline-block;width: 100%;position:relative;">
									<span id="timeStrTip" class="defaultTipBox">00:00:00</span>
									<input id="timeTrack" type="range" value="0" step="1" min="0">
								</span>
							</span>
						</div>
					</div>
					<div class="footTool">
						<span class="no-padding">
							<img src="/jfplayer/web/img/play.png" class="left" id="btnPlayVideo" @click="playVideo()" data-i18n="Play/Pause/Resume/Refresh/Cancel frame-by-frame playback" title="播放/暂停/恢复/刷新/取消按帧播放" />
						</span>
            			<span class="no-padding playbackModule" style=" padding-left:5px;">
							<img src="/jfplayer/web/img/FastRewind.png" class="left" id="btnFastRewindVideo" @click="fastRewindVideo()" data-i18n="Back off" title="后退" />
						</span>
						<span class="no-padding" style=" padding-left:5px;">
							<img src="/jfplayer/web/img/stop.png" class="left" id="btnStopVideo" @click="stopVideo()" data-i18n="Stop" title="停止" />
						</span>
						<span class="no-padding playbackModule" style=" padding-left:5px;">
						<img src="/jfplayer/web/img/FastPlayback.png" class="left" id="btnFastPlaybackVideo" @click="fastPlaybackVideo()" data-i18n="Fast forward" title="快进" />
						</span>
						<span class="no-padding playbackModule" style=" padding-left:5px;">
							<img src="/jfplayer/web/img/nextFrame.png" class="left" id="btnNextFrame" @click="playNextFrame()" data-i18n="The next frame" title="下一帧" />
						</span>

						<span class="no-padding playbackModule" style=" padding-left:10px;">
							<label id="timeLabel">00:00:00/00:00:00</label>
						</span>



						<span class="no-padding right">
							<img src="/jfplayer/web/img/fullscreen.png" class="right" id="btnFullscreen" @click="fullscreen()" data-i18n="Full screen" title="全屏" />
							<img src="/jfplayer/web/img/cancelFullscreen.png" class="right" id="btnCancelFullscreen" style="display: none;" @click="exitfullscreen()" data-i18n="Exit Full Screen" title="退出全屏" />
						</span>
						<div class="no-padding right">
							<img src="/jfplayer/web/img/volume.png" class="right" id="btnVolume" data-i18n="Volume" title="音量" />
							<input type="range" id="volumeTrack" class="vertical-range" value="1" step="0.1" min="0" max="1" style="position: relative;top: -90px;left: -40px;display: none;">
						</div>
						<div class="no-padding right">
							<img src="/jfplayer/web/img/capture.png" class="right" id="btnCaptureVideo" @click="playCapture()" data-i18n="Screenshot" title="截图" />
						</div>
						<!-- <div class="no-padding right">
							<img src="/jfplayer/web/img/digitZoom.png" class="right" id="btnDigitZoomVideo" @click="playZoom()" data-i18n="Digital amplification" title="数字放大" />
						</div> -->
						<div class="no-padding right previewModule decoderWasmModule" style="display: none;">
							<img src="/jfplayer/web/img/setting.png" class="right" id="btnColorVideo" data-i18n="Color settings" title="颜色设置" />
							<div class="color-range" style="position: relative;top: -177px;left: -55px;width: 180px; height: 165px;background-color: white;padding: 10px 5px;border-radius: 5px;display: none;">
								<div style="display: flex;">
									<img src="/jfplayer/web/img/brightness.png" class="right" @click="" data-i18n="Brightness" title="亮度" />
									<input type="range" title="亮度" id="colorBrightnessTrack" value="64" step="1" min="0" max="128" style="float: left;width: 129px;">
								</div>
								<div style="display: flex;">
									<img src="/jfplayer/web/img/contrast.png" class="right" @click="" data-i18n="Contrast" title="对比度" />
									<input type="range" title="对比度" id="colorContrastTrack" value="64" step="1" min="0" max="128" style="float: left;width: 129px;">
								</div>
								<div style="display: flex;">
									<img src="/jfplayer/web/img/hue.png" class="right" @click="" data-i18n="hue" title="色调" />
									<input type="range" title="色调" id="colorHueTrack" value="64" step="1" min="0" max="128" style="float: left;width: 129px;">
								</div>
								<div style="display: flex;">
									<img src="/jfplayer/web/img/saturation.png" class="right" @click="" data-i18n="Saturation" title="饱和度" />
									<input type="range" data-i18n="Saturation" title="饱和度" id="colorSaturationTrack" value="64" step="1" min="0" max="128" style="float: left;width: 129px;">
								</div>
								<button type="button" class="custom-btn outline-btn" style="width: 160px !important;" @click="playSetColor()" data-i18n="Default">默认配置</button>
							</div>
						</div>
						<div class="no-padding right talkModule " style="display: none;">
							<img src="/jfplayer/web/img/audio.png" class="right" id="btnAudioVideo" @click="playVoice()" data-i18n="Intercom" title="对讲" />
						</div>
						<div class="no-padding right">
							<img src="/jfplayer/web/img/recorder.png" class="right" id="btnRecoderDownload" @click="recoderDownload()" data-i18n="Recorded broadcast" title="录播" />
						</div>
						<div class="no-padding right">
							<img src="/jfplayer/web/img/clearConsole.png" class="right" id="btnClearConsole" @click="clearConsole()" data-i18n="Clear the console" title="清除控制台" />
						</div>
					</div>

				</div>



				<div class="module_middle_console">
					<!-- 标题 -->
					<div class="module_label">
						<div class="module_lable_item"></div>
						<div class="module_lable_item_content" data-i18n="Console">控制台</div>
					</div>
					<div class="console-body" id="consoleOutput">
						<!-- 控制台输出-->
					</div>

				</div>
			</div>

			<!-- 右边模块 -->
			<div class="module_right">
				<div class="tabs-container">
					<div class="tabs-header">
						<button class="tab-btn active" data-tab="info1" data-i18n="Dynamic">动态信息</button>
						<button class="tab-btn " data-tab="info2" data-i18n="Basic">基本信息</button>
						<button class="tab-btn " data-tab="info3" data-i18n="Browser">浏览器信息</button>
					</div>

					<div class="tabs-content">
						<div class="tab-panel active" id="info1-tab">
							<div class="console-message">
								<div class="timestamp itemLabel" data-i18n="Frame rate monitoring">帧率监控</div>
								<div class="message-content info"></div>
							</div>
							<div class="console-message">
								<div class="timestamp" data-i18n="Current Fps(f/s)">当前FPS(帧/秒)</div>
								<div class="message-content info" id="currentFps">0</div>
							</div>
							<div class="console-message">
								<div class="timestamp" data-i18n="Rendered frames(Total)">已渲染帧数(总帧数)</div>
								<div class="message-content info" id="renderedFrames">0</div>
							</div>
							<div class="console-message">
								<div class="timestamp " data-i18n="--Smoothness">流畅度</div>
								<div class="message-content info" id="smoothness">--</div>
							</div>

							<div class="console-message">
								<div class="timestamp itemLabel" data-i18n="Memory usage">内存使用</div>
								<div class="message-content info"></div>
							</div>
							<div class="console-message">
								<div class="timestamp" data-i18n="Used Memory(MB)">已使用内存(MB)</div>
								<div class="message-content info" id="usedMemory">0</div>
							</div>
							<div class="console-message">
								<div class="timestamp" data-i18n="Total memory(MB)">总内存(MB)</div>
								<div class="message-content info" id="totalMemory">0</div>
							</div>
							<div class="console-message">
								<div class="timestamp" data-i18n="Memory usage(%)">使用率(%)</div>
								<div class="message-content info" id="memoryUsage">0</div>
							</div>


							<div class="console-message">
								<div class="timestamp itemLabel" data-i18n="Processor Information">处理器信息</div>
								<div class="message-content info"></div>
							</div>
							<div class="console-message">
								<div class="timestamp" data-i18n="cpu Cores">CPU核心数</div>
								<div class="message-content info" id="cpuCores">0</div>
							</div>
							<div class="console-message">
								<div class="timestamp" data-i18n="Device memory(GB)">设备内存(GB)</div>
								<div class="message-content info" id="deviceMemory">0</div>
							</div>
							<div class="console-message">
								<div class="timestamp" data-i18n="Battery level(%)">电池状态(%)</div>
								<div class="message-content info" id="batteryLevel">0</div>
							</div>


							<div class="console-message">
								<div class="timestamp itemLabel" data-i18n="Network status">网络状态</div>
								<div class="message-content info"></div>
							</div>
							<div class="console-message">
								<div class="timestamp" data-i18n="Network type">连接类型</div>
								<div class="message-content info" id="networkType">--</div>
							</div>
							<div class="console-message">
								<div class="timestamp" data-i18n="Downlink speed(Mbps)">下载速度(Mbps)</div>
								<div class="message-content info" id="downlinkSpeed">0</div>
							</div>
							<div class="console-message">
								<div class="timestamp" data-i18n="Network Rtt(ms)">网络延迟(ms)</div>
								<div class="message-content info" id="networkRtt">0</div>
							</div>


							<div class="console-message">
								<div class="timestamp itemLabel" data-i18n="Long task monitoring">长任务监控</div>
								<div class="message-content info"></div>
							</div>
							<div class="console-message">
								<div class="timestamp" data-i18n="Long tasks count(ms)">长任务数量(个)</div>
								<div class="message-content info" id="longTasksCount">0</div>
							</div>
							<div class="console-message">
								<div class="timestamp" data-i18n="Last long task(ms)">最近长任务(ms)</div>
								<div class="message-content info" id="lastLongTask">0</div>
							</div>
							<div class="console-message">
								<div class="timestamp" data-i18n="Blocking time(ms)">阻塞时间(ms)</div>
								<div class="message-content info" id="blockingTime">0</div>
							</div>

							<div class="console-message">
								<div class="timestamp itemLabel" data-i18n="Rendering performance">渲染性能</div>
								<div class="message-content info"></div>
							</div>
							<div class="console-message">
								<div class="timestamp" data-i18n="FCP(ms)">FCP(ms)</div>
								<div class="message-content info" id="fcpTime">0</div>
							</div>
							<div class="console-message">
								<div class="timestamp" data-i18n="LCP(ms)">LCP(ms)</div>
								<div class="message-content info" id="lcpTime">0</div>
							</div>

						</div>
						<div class="tab-panel " id="info2-tab">

						</div>
						<div class="tab-panel" id="info3-tab">

						</div>

					</div>

				</div>

			</div>

		</div>
		<div id="footer">&copy; 2025 Zhejiang JAIFY Co., Ltd.</div>

		<!-- 弹框模块 -->
		<div id="messageModal" class="modal-overlay" style="display: none;">
			<div class="modal-container">
				<div class="modal-header">
					<span class="modal-title" id="modalTitle" data-i18n="Instructional message">提示信息:</span>
					<button class="modal-close" onclick="hideModal()">&times;</button>
				</div>
				<div class="modal-body">
					<div class="modal-row">
						<span class="modal-label" data-i18n="Error code">错误码：</span>
						<span class="modal-value" id="errorUserCode">-</span>
					</div>
					<div class="modal-row">
						<span class="modal-label" data-i18n="Error message">错误内容：</span>
						<span class="modal-value" id="errorUserMsg">-</span>
					</div>
					<div class="modal-row">
						<span class="modal-label" data-i18n="Error level">消息等级：</span>
						<span class="modal-value" id="errorLevel">-</span>
					</div>
					<div class="modal-row">
						<span class="modal-label" data-i18n="Error type">错误类型：</span>
						<span class="modal-value" id="errorCategory">-</span>
					</div>
					<div class="modal-row">
						<span class="modal-label" data-i18n="Error action">操作建议：</span>
						<span class="modal-value" id="errorAction">-</span>
					</div>
				</div>
				<div class="modal-footer">
					<a href="https://docs.jftech.com/docs?menusId=54582398fd8d4248962354e92ac2e47a&siderId=6b580eb6f66349dabbd79c905544287b&lang=zh" class="modal-btn modal-btn-primary" target="_blank" onclick="hideModal();" data-i18n="Learn more">了解更多</a>
					<button class="modal-btn" onclick="hideModal()" data-i18n="OK">确定</button>
				</div>
			</div>
		</div>
	</template>
<script setup>
import { onMounted } from 'vue';
import {
  Logger,
  emState_Idle,
  emState_Running,
  emState_Pausing,
  g_playDecodeType,
  CallBack_Error,
  CallBack_Loading,
  CallBack_Stop,
  CallBack_Pause,
  CallBack_Playing,
  CallBack_Finished,
  CallBack_Timeout,
  CallBack_Abort,
  CallBack_PlaybackMsg,
  CallBack_HttpErrMsg,
  CallBack_parseFrame,
  CallBack_playReconnect,
  CallBack_ChangeDecodeMode,
  CallBack_OutputConsole,
  CallBack_DevicePRI_Msg,
  CallBack_Talk_Start,
  CallBack_Talk_Failed,
  CallBack_Talk_Stop,
  g_nLogLv_Error,
  g_nLogLv_Warn,
  g_nLogLv_Info,
  g_nLogLv_Debug,
  g_nLogLv_All,
} from '../../../public/jfplayer/common';
import { Player } from '../../../public/jfplayer/player'

//组件
import browser from '../../../public/jfplayer/web/debug/browserES.min.js';
import PerformanceMonitor from "../../../public/jfplayer/web/debug/performance.js";

const props = defineProps({
  src: String,
  width: Number,
  height: Number,
  bufferTime: {
    type: Number,
    default: 300
  },
  isStream: {
    type: Boolean,
    default: true
  },
  speed: {
    type: String,
    default: '1.0'
  },
  enableHEVC: {
    type: Boolean,
    default: false
  }
})

let langItem = "point_language";
let langDocm = ""
let lang = "zh-CN"
// 初始化国际化
let point_language = window.sessionStorage.getItem(langItem)
let userLang = navigator.language || 'en';

let protoList, inputUrl, eleStreamType, eleSpeed, bufferTime, logLevel, lastFrame, previewReconn, timeTrackDoc, timeTrack, timeLabel, timeDocTip, reconnInterval, playbackReplay, decodingType, canvas1, context1,loadingDiv,flvVideoEle,logger,fastForwardInterval,deviceIP,devicePort,deviceUsername,devicePassword,deviceChannel,deviceStream,fileSelector,webRTCTalkTypeList,webRTCTalkUrl,webRTCLocalVideo,isLocalFile
function initInfo() {
  langDocm = document.getElementById("languageType")	
  protoList = document.getElementById("protocol"); //视频格式
  inputUrl = document.getElementById("inputUrl"); //视频地址
  eleStreamType = document.getElementById("streamType"); //播放模式
  eleSpeed = document.getElementById("speed"); //播放速率
  bufferTime = document.getElementById("bufferTime"); //缓冲时长
  decodingType = document.getElementById("decodingType"); //解码模式
  logLevel = document.getElementById("logLevel"); //日志等级
  lastFrame = document.getElementById("lastFrame"); //预览追帧
  previewReconn = document.getElementById("previewReconn"); //预览重连
  reconnInterval = document.getElementById("reconnInterval"); //预览重连间隔
  playbackReplay = document.getElementById("playbackReplay"); //回放结束重播
  fastForwardInterval = document.getElementById("fastForwardInterval"); //快进、后退间隔

  //PRI(device) 配置项
  deviceIP = document.getElementById("deviceIP"); //设备信息——IP
  devicePort = document.getElementById("devicePort"); //设备信息——web端口
  deviceUsername = document.getElementById("deviceUsername"); //设备信息——账号
  devicePassword = document.getElementById("devicePassword"); //设备信息——密码
  deviceChannel = document.getElementById("deviceChannel"); //设备信息——通道序号
  deviceStream = document.getElementById("deviceStream"); //设备信息——码流类型

  fileSelector = document.getElementById('fileSelector');

  timeTrackDoc = document.getElementById("timeTrack");
  timeTrack = document.getElementById("timeTrack");
  timeLabel = document.getElementById("timeLabel");
  timeDocTip = document.getElementById("timeStrTip");
  
  //webRTC
  webRTCTalkTypeList = document.getElementById("webRTCTalkType"); //webRTC 对讲类型
  webRTCTalkUrl = document.getElementById("webRTCTalkUrl"); //webRTC 单项对讲地址
  webRTCLocalVideo = document.getElementById("localVideo"); //webRTC 本地视频

  canvas1 = document.getElementById("playCanvas1");
  context1 = canvas1.getContext("2d");
  var imgX = 0;
  var imgY = 0;
  var imgScale = 1;
  var img = new Image();
  img.src = '/jfplayer/web/img/logo.png';
  //图片加载完后，将其显示在canvas中
  img.onload = function () {
    var bg = context1.createPattern(img, "no-repeat"); //createPattern() 方法在指定的方向内重复指定的元素。
    var scale_H = img.height > canvas1.height ? canvas1.height / img.height : 1;
    var scale_W = img.width > canvas1.width ? canvas1.width / img.width : 1;
    imgScale = scale_H > scale_W ? scale_W : scale_H;
    var img_H = img.height * imgScale;
    var img_W = img.width * imgScale;
    imgX = (canvas1.width - img_W) / 2;
    imgY = (canvas1.height - img_H) / 2;
    context1.fillStyle = bg; //fillStyle 属性设置或返回用于填充绘画的颜色、渐变或模式。
    context1.drawImage(img, 0, 0, img.width, img.height, imgX, imgY, img_W, img_H);
  }
  langItem = "point_language";
  langDocm = document.getElementById("languageType")

  // 初始化国际化
  point_language = window.sessionStorage.getItem(langItem)
  userLang = navigator.language || 'en';
  if (point_language) {
    userLang = point_language;
    langDocm.value = point_language;
  }
  lang = ['zh-CN', 'en'].includes(userLang) ? userLang : 'en';
  initI18n(lang);

  
  //Player object.
  self.player = new Player({
    dir: '/jfplayer',
    appkey: null, //鉴权配置 appKey
    uuid: null, //鉴权配置 uuid
    appsecret: null, //鉴权配置 appSecret
    movedcard: null ,//鉴权配置 movedcard

    //其他配置
    logLevel: Number(logLevel.value), //打印日志等级
    outputConsole: true, //UI控制台输出
    outputConsoleFun: printMessage, //指定输出回调
  });

  //设置loading元素绑定
  loadingDiv = document.getElementById("loading");
  self.player.fnSetLoadingDiv(loadingDiv);

  //硬解video元素绑定
  flvVideoEle = document.getElementsByName('videoElement')[0];
  self.player.fnSetVideoEle(flvVideoEle, webRTCLocalVideo);

  //Formated logger.
  logger = new Logger("Page", self.player.options);

  isLocalFile = false;//是否是本地文件


  // 监听 input 事件
  timeTrackDoc.addEventListener('input', function () {
    self.player.m_nFlag_SkipOpt = true;
  });
  // 监听 change 事件
  timeTrackDoc.addEventListener('change', function () {
    logger.logInfo('Range input value changed to: ', this.value);
    var currentState = self.player.fnGetState();
    if (self.player.m_fDurationSecs > 0 && self.player.m_fDurationSecs != self.player.m_tPtsLast) {
      let time = Math.floor(this.value);
      changeSkipTime(time);
    }
  });

  timeTrack.removeEventListener('change', () => { });
  timeTrack.addEventListener('mouseenter', () => {
    timeDocTip.style.display = 'inline-block'
  });
  timeTrack.addEventListener('mouseleave', () => {
    timeDocTip.style.display = 'none'
  });
  // 监听 mousemove 事件
  timeTrack.addEventListener('mousemove', function (e) {
    let progressBar = e.target;
    let rect = progressBar.getBoundingClientRect();
    let offsetX = e.clientX - rect.left;
    let maxSeconds = e.target?.max
    let timeStr = "00:00:00";
    if (self.player.m_fDurationSecs > 0) {
      let progress = offsetX / rect.width;
      let seconds = maxSeconds * progress;
      if (seconds < 0) {
        timeStr = "00:00:00";
      } else if (progress >= 0.99) {
        timeStr = self.player.fnFormatTime(maxSeconds);
      } else {
        // Format the time string
        timeStr = self.player.fnFormatTime(seconds);
      }
    }
    timeDocTip.style.left = `${offsetX}px`;
    timeDocTip.innerHTML = timeStr;
  });


  //音频操作
  var volumeBtnDoc = document.getElementById("btnVolume");
  var volumeInput = document.querySelector('.vertical-range');
  // 当用户点击input时显示  
  volumeBtnDoc.addEventListener('mouseover', function () {
    volumeInput.style.display = '';
    volumeInput.disabled = false;
  });
  volumeInput.addEventListener('mouseover', function () {
    volumeInput.style.display = '';
    volumeInput.disabled = false;
  });
  // 当input失去焦点时隐藏  
  volumeBtnDoc.addEventListener('mouseout', function () {
    volumeInput.style.display = 'none';
    volumeInput.disabled = true;
  });
  volumeInput.addEventListener('mouseout', function () {
    volumeInput.style.display = 'none';
    volumeInput.disabled = true;
  });
  // 监听 change 事件
  volumeInput.addEventListener('change', function () {
    logger.logInfo('Volume input value changed to: ', this.value);
    self.player.fnChangeSound(this.value);
  });


  //颜色操作
  var colorBtnDoc = document.getElementById("btnColorVideo");
  var colorInput = document.querySelector('.color-range');
  // 当用户点击input时显示  
  colorBtnDoc.addEventListener('mouseover', function () {
    colorInput.style.display = '';
    colorInput.disabled = false;
  });
  colorInput.addEventListener('mouseover', function () {
    colorInput.style.display = '';
    colorInput.disabled = false;
  });
  // 当input失去焦点时隐藏  
  colorBtnDoc.addEventListener('mouseout', function () {
    colorInput.style.display = 'none';
    colorInput.disabled = true;
  });
  colorInput.addEventListener('mouseout', function () {
    colorInput.style.display = 'none';
    colorInput.disabled = true;
  });
  var colorBrightnessTrack = document.getElementById("colorBrightnessTrack");
  var colorContrastTrack = document.getElementById("colorContrastTrack");
  var colorHueTrack = document.getElementById("colorHueTrack");
  var colorSaturationTrack = document.getElementById("colorSaturationTrack");
  // 监听 change 事件
  //颜色--亮度
  colorBrightnessTrack.addEventListener('change', function () {
    self.player.fnSetBrightness(this.value);
  });
  //颜色--对比度
  colorContrastTrack.addEventListener('change', function () {
    self.player.fnSetContrast(this.value);
  });
  //颜色--色调
  colorHueTrack.addEventListener('change', function () {
    self.player.fnSetHue(this.value);
  });
  //颜色--饱和度
  colorSaturationTrack.addEventListener('change', function () {
    self.player.fnSetSaturation(this.value);
  });
  const tabButtons = document.querySelectorAll('.tab-btn');
  tabButtons.forEach(button => {
    button.addEventListener('click', () => {
      // 移除所有按钮的active类
      tabButtons.forEach(btn => btn.classList.remove('active'));

      // 添加active类到当前按钮
      button.classList.add('active');

      // 获取目标标签ID
      const targetTab = button.getAttribute('data-tab');

      // 隐藏所有内容面板
      document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.remove('active');
      });

      // 显示目标内容面板
      document.getElementById(`${targetTab}-tab`).classList.add('active');
    });
  });


	// 监听文件选择事件
	fileSelector.addEventListener('change', (e) => {
		// 获取用户选择的文件（只取第一个）
		const selectedFile = e.target.files[0];
		if (!selectedFile) return; // 未选择文件则退出

		// // 验证文件类型是否为MP4
		// if (selectedFile.type !== 'video/mp4') {
		// 	alert('请选择MP4格式的视频文件！');
		// 	return;
		// }

		// 创建临时URL（浏览器内存中的临时路径）
		const videoUrl = URL.createObjectURL(selectedFile);
		inputUrl.value = videoUrl;
				
	});

  
			window.hideModal = function() {
				const modal = document.getElementById('messageModal');
				modal.style.display = 'none';
			};

			// 点击遮罩层关闭弹框
			document.getElementById('messageModal').addEventListener('click', function(e) {
				if (e.target === this) {
					hideModal();
				}
			});

			// ESC键关闭弹框
			document.addEventListener('keydown', function(e) {
				if (e.key === 'Escape') {
					hideModal();
				}
			});

}

function playVideo() {
  var proto = protoList.options[protoList.selectedIndex].value;
  var webRTCTalkType = webRTCTalkTypeList.options[webRTCTalkTypeList.selectedIndex].value;
  var inputUrl = document.getElementById("inputUrl");
  var url = inputUrl.value;

  var bIsStream = eleStreamType.selectedIndex == 0;
  var nSpeed = eleSpeed.options[eleSpeed.selectedIndex].value;

  var inputVolume = document.getElementById("volumeTrack");
  var nVolume = inputVolume.value;

  //解码方式
  var enableHEVC = parseBoolean(decodingType.value);
  //缓冲时长
  var bufferTimeConfig = Number(bufferTime.value);
  //预览追帧
  var enableLastFrame = parseBoolean(lastFrame.value);
  //预览重连
  var enablePreviewReconn = parseBoolean(previewReconn.value);
  var reconnNumberConfig = Number(reconnNumber.value); //重连次数
  var reconnIntervalConfig = Number(reconnInterval.value); //重连间隔
  //回放结束重播
  var enablePlaybackReplay = parseBoolean(playbackReplay.value);
  //快进、后退间隔
  var fastForwardIntervalConfig = Number(fastForwardInterval.value);

  var el = document.getElementById("btnPlayVideo");
  var currentState = self.player.fnGetState();
 

  if (currentState == emState_Idle) {
    console.debug("=======初始播放========");
    const canvasId = "playCanvas";
    var canvas = document.getElementById(canvasId);
    self.player.fnStop();
    if (!canvas) {
      logger.logError("No Canvas with id " + canvasId + "!");
      return false;
    }

    //切换canvas 、video的隐藏与显示（软解使用canvas，硬解使用video）
    onSelectDecoderRender();

	self.player.fnPlay({
		/*--------基础配置项----------*/
		url: url, //播放地址
		isStream: bIsStream, //预览：true，回放:false,
		urlProto: proto, //类型：flv,hls

		/*--回放配置项,如果url字符串中含有startTime、endTime,则不需要配置下面配置项 ，例如：startTime=20250202000000&endTime=20250203000000--*/
		startDate: '2024-11-26 16:30:00', //回放开始时间 ,YYYY-MM-DD HH:mm:ss 的格式
		endDate: '2024-11-26 17:00:10', //回放结束时间,YYYY-MM-DD HH:mm:ss 的格式

		/*-------可选择配置项-------*/
		speed: Number(nSpeed), //播放倍速(范围：(0,16] )
		volume: Number(nVolume), //音量大小(范围：[0,1])
		enableHEVC: enableHEVC, //软解:false ,硬解:true
		frameTracking: enableLastFrame, //预览，是否实时追帧(启用：true ,禁用：false)
		reconnect: enablePreviewReconn, //预览，是否重连(启用：true ,禁用：false)
		reconnectInterval: Number(reconnIntervalConfig), //预览，重连间隔，单位：毫秒(范围：(0,60000] )
		maxReconnectAttempts: Number(reconnNumberConfig), //预览，重连次数 (范围:(0,正无穷大))
		bufferTime: Number(bufferTimeConfig), //缓冲区间, 单位：毫秒(范围：(0,60000])
		restartPlayback: enablePlaybackReplay, //回放结束播放后，重新开始播放(启用：true ,禁用：false)
		fastForwardInterval: Number(fastForwardIntervalConfig), //快进、后退的间隔基数,单位：毫秒(范围:(0,3600000] ))
		// secure: false, //是否启用https，限PRI(Device)协议(启用：true ,禁用：false)
		// recordMaxFileSize: Number(1024 * 1024), //录制文件大小限制，单位：字节,(范围：[1024 * 1024 , 500 * 1024 * 1024] )
		// scaleMode: "contain", //缩放模式：'contain'(留边) | 'cover'(全铺) ，限软解模式,(枚举值：'contain' , 'cover')
		// aspectRatio: Number(4 / 3), //宽高比,例如：4/3  ，限软解模式下的留边模式，(枚举值： 16 / 9, 4 / 3, 1 / 1, 9 / 16, 3 / 4, 3 / 2, 5 / 4, 16 / 10)

		// 对讲音频配置（如果是设备私有协议，请结合实际的通道能力集信息配置）
		audioConfig: {
			sampleBits: 16, //采样位数
			sampleRate: 8000, //采样率
		},

		//对讲(webRTC/priDevice)
		talkMode: webRTCTalkType, //对讲类型(单、双)
		talkUrl: webRTCTalkUrl.value, //适用webRTC单向对讲 、priDevice设备对讲
		deviceType: 0, //设备类型(仅对devicePRI有效)，配合devicePRI的previewOptions 配置适用，(枚举值：IPC：0，非IPC：1)
		isLocalFile: isLocalFile, //是否是本地文件

		//预览配置项
		previewOptions: {
			ip: deviceIP.value,
			httpPort: devicePort.value,
			userName: deviceUsername.value,
			loginPsw: devicePassword.value,
			Channel: deviceChannel.value,
			Stream: deviceStream.options[deviceStream.selectedIndex].value,
		},
		//回放配置项
		playbackOptions: {
			"Name": "HttpPlayBack",
			"HttpPlayBack": {
				"Opr": "StartPlay",
				"PlayMode": "PlayByName",
				"Channel": 0,
				"Stream": "Main",
				"ExactSeek": 1,
				"PlayByName": {
					"LocalTime": "2025-09-04 00:00:00",
					"FileName": "/idea0/2025-09-04/001/00.00.00-01.00.00[R][@a4bff][0].h264"
				}
			},
			"Salt": "mc54Ztof"
		},
	}, canvas, function(e) {
		switch (e.ret) {
			case CallBack_Error: //抛出异常
				// logger.logError("CallBack_Error:" + e.error ? e.error : e.ret + " status:" + e.status + " message:", e.message);
				break;
			case CallBack_Loading: //加载中
				// logger.logInfo("CallBack_Loading ret " + e.ret + " status:" + e.status + " message:", e.message);
				break;
			case CallBack_Stop: //播放停止
				// logger.logInfo("CallBack_Stop ret " + e.ret + " status:" + e.status + " message:", e.message);
				el.src = "/jfplayer/web/img/play.png";
				break;
			case CallBack_Pause: //播放暂停
				// logger.logInfo("CallBack_Pause ret " + e.ret + " status:" + e.status + " message:", e.message);
				if (bIsStream) {
					el.src = "/jfplayer/web/img/replay.png";
				} else {
					el.src = "/jfplayer/web/img/play.png";
				}
				break;
			case CallBack_Playing: //播放中
				// logger.logInfo("CallBack_Playing ret " + e.ret + " status:" + e.status + " message:", e.message);
				if (bIsStream) {
					el.src = "/jfplayer/web/img/replay.png";
				} else {
					el.src = "/jfplayer/web/img/pause.png";
				}
				break;
			case CallBack_Finished: //播放完成
				// logger.logInfo("CallBack_Finished ret " + e.ret + " status:" + e.status + " message:", e.message);
				el.src = "/jfplayer/web/img/play.png";
				break;
			case CallBack_Timeout: //请求超时
				// logger.logInfo("CallBack_Timeout ret " + e.ret + " status:" + e.status + " message:", e.message);
				break;
			case CallBack_Abort: //请求中断
				// logger.logInfo("CallBack_Abort ret " + e.ret + " status:" + e.status + " message:", e.message);
				break;
			case CallBack_PlaybackMsg: //回放消息推送
				// logger.logInfo("CallBack_PlaybackMsg ret " + e.ret + " status:" + e.status + " message:", e.message);

				//TODO  在这里做窗口同步播放
				//第一步，更新main的时间基准  e.message.msg
				//第二步，将时间基准传入 方法 fnWinSyncPlay(date) ，date格式：YYYY-MM-dd HH:mm:ss 

				break;
			case CallBack_HttpErrMsg: //http请求异常消息推送
				// logger.logInfo("CallBack_HttpErrMsg ret " + e.ret + " status:" + e.status + " message:", e.message);
				break;
			case CallBack_parseFrame: //frame 数据解析
				// logger.logInfo("CallBack_parseFrame ret " + e.ret + " status:" + e.status + " message:", e.message);
				break;
			case CallBack_playReconnect: //重连消息推送
				// logger.logInfo("CallBack_playReconnect ret " + e.ret + " status:" + e.status + " message:", e.message);
				break;
			case CallBack_ChangeDecodeMode: //切换解码模式	
				// logger.logInfo("CallBack_ChangeDecodeMode ret " + e.ret + " status:" + e.status + " message:", e.message);
				//切换显示元素
				// let msg = e.message;
				// if (msg.decoderType == g_playDecodeType[0]) { //软解
				// 	gwmModule.style.display = "block";
				// 	flvModule.style.display = "none";
				// } else if (msg.decoderType == g_playDecodeType[1]) { //硬解
				// 	gwmModule.style.display = "none";
				// 	flvModule.style.display = "block";
				// }
				break;
			case CallBack_OutputConsole: //输出控制台消息
				printMessage(e.message);
				break;
			case CallBack_DevicePRI_Msg: //devicePRI协议响应体（cgi\ws）消息推送
				// logger.logInfo("CallBack_DevicePRI_Msg ret " + e.ret + " status:" + e.status + " message:", e.message);
				break;
			case CallBack_Talk_Start: //对讲开始
				// logger.logInfo("CallBack_Talk_Success ret " + e.ret + " status:" + e.status + " message:", e.message);
				break;
			case CallBack_Talk_Failed: //对讲失败
				// logger.logInfo("CallBack_Talk_Failed ret " + e.ret + " status:" + e.status + " message:", e.message);
				break;
			case CallBack_Talk_Stop: //对讲停止
				// logger.logInfo("CallBack_Talk_Stop ret " + e.ret + " status:" + e.status + " message:", e.message);
				break;
			default:
				break;
		}

		//弹框提示
		if (e.message) {
			showModal(e.message);
		}
	});
	self.player.fnSetBufferTime(bufferTimeConfig);
	self.player.fnSetCbAiInfo(function(e) {
		console.log("k " + e.k + " w:" + e.w + " h:" + e.h + ".");
		const deco = new TextDecoder();
		strmsg = deco.decode(e.m);
		console.log("aiJson: " + strmsg);
	});

	//self.player.fnSetRealTime(false);
	//self.player.fnSetBufferTime(4e3);

	var progressBarModal = document.getElementById("progressBar_div");
	self.player.fnSetTrack(timeTrack, timeLabel, progressBarModal);
} else if (currentState == emState_Running) { //恢复播放转暂停播放
	console.debug("=======暂停/重新播放========");
	self.player.fnPause();
} else if (currentState == emState_Pausing) { //暂停播放转恢复播放
	console.debug("=======恢复播放========");
	self.player.fnResume();
} else { //其他
	console.debug("=======暂停播放2========");
	self.player.fnPause();
}

  return true;
}

//停止播放
function stopVideo() {
  console.debug("=======停止播放========");
  self.player.fnDestroy();
  baseInfo_DynamicData_Stop();
}

//快退
function fastRewindVideo() {
	console.debug("=======后退========");
	self.player.fnFastRewind();
}

//快进
function fastPlaybackVideo() {
	console.debug("=======快进========");
	self.player.fnFastPlayback();
}

//下一帧
function playNextFrame() {
  console.debug("=======下一帧========");
  self.player.fnPlayNextFrame();
}

//全屏
const fullscreen = function () {
  console.debug("=======全屏========");
  self.player.fnFullscreen();
}

//退出全屏
const exitfullscreen = function () {
  console.debug("=======退出全屏========");
  self.player.fnExitFullscreen()
}
//切换全屏状态
const toggleFullscreen = function() {
	if (document.fullscreenElement) {
		exitfullscreen();
	} else {
		fullscreen();
	}
}
//监听全屏变化
document.addEventListener("fullscreenchange", function (event) {
	if (document.fullscreenElement) {
		document.addEventListener('mousemove', showCanvasFoot);
		document.addEventListener('mouseleave', hideCanvasFoot);
		document.getElementById("btnFullscreen").style.display = "none";
		document.getElementById("btnCancelFullscreen").style.display = "";
	} else {
		document.removeEventListener('mousemove', showCanvasFoot);
		document.removeEventListener('mouseleave', hideCanvasFoot);
		document.getElementById("btnFullscreen").style.display = "";
		document.getElementById("canvasFoot").style.display = "";
		document.getElementById("btnCancelFullscreen").style.display = "none";
		var canvasFoot = document.getElementById("canvasFoot");
		canvasFoot.style.display = "block";
	}

});

function showCanvasFoot(event) {
	var canvasFoot = document.getElementById("canvasFoot");
	if (window.innerHeight - event.clientY < 50) {
		canvasFoot.style.display = "block";
		canvasFoot.disabled = false;
	} else {
		canvasFoot.style.display = "none";
		canvasFoot.disabled = true;
	}
}

function hideCanvasFoot() {
	var canvasFoot = document.getElementById("canvasFoot");
	// canvasFoot.style.display = "none";
	// canvasFoot.disabled = true;
}
//视频格式
const onSelectProtocol = function () {
  var eleModule = document.getElementsByClassName("decoderModule");
  [...eleModule].forEach(item => {
    item.style.display = "none";
	  item.disabled = true;
  });
  var elePriModule_url = document.getElementsByClassName("devicePreviewModule_children_url");
  var elePriModule_info = document.getElementsByClassName("devicePreviewModule_children_info");
  var eleMP4Module_url = document.getElementsByClassName("mp4PlaybackModule_children_url");
  var eleMP4Module_info = document.getElementsByClassName("mp4PlaybackModule_children_info");
  var eleWebRTCTalkModule_one = document.getElementsByClassName("webRTCTalkModule_children_oneTalk");
  var eleWebRTCTalkModule_two = document.getElementsByClassName("webRTCTalkModule_children_twoTalk");
  var elePriModuleLocal_url = document.getElementsByClassName("devicePlaybackModule_children_url");
  var elePriModuleLocal_info = document.getElementsByClassName("devicePlaybackModule_children_info");
  [...elePriModule_url].forEach(item => {
		item.style.display = null;
		item.disabled = false;
  });
  [...elePriModule_info].forEach(item => {
		item.style.display = "none";
		item.disabled = true;
  });
  [...eleMP4Module_url].forEach(item => {
		item.style.display = null;
		item.disabled = false;
  });
  [...eleMP4Module_info].forEach(item => {
		item.style.display = "none";
		item.disabled = true;
  });
  [...eleWebRTCTalkModule_one].forEach(item => {
		item.style.display = "none";
		item.disabled = true;
  });
  [...eleWebRTCTalkModule_two].forEach(item => {
		item.style.display = "none";
		item.disabled = true;
  });
  [...elePriModuleLocal_url].forEach(item => {
		item.style.display = null;
		item.disabled = false;
  });
  [...elePriModuleLocal_info].forEach(item => {
		item.style.display = "none";
		item.disabled = true;
  });
  var priConfigEle = document.getElementById("priConfigModule");
  priConfigEle.value = "url";
  var mp4ConfigEle = document.getElementById("mp4ConfigModule");
  mp4ConfigEle.value = "url";
  var webRTCTalkEle = document.getElementById("webRTCTalkType");
  webRTCTalkEle.value = "one-way-video";

  var eleProtocol = document.getElementById("protocol");
  var dataDecoder = eleProtocol.selectedOptions[0].attributes["data-decoder"].value;
  var dataSpeed = eleProtocol.selectedOptions[0].attributes["data-speed"];
  var dataSpeedDisabled = eleProtocol.selectedOptions[0].attributes["data-speed-disabled"];
  let arr = dataDecoder.split(" ");
  for (var i = 0; i < arr.length; i++) {
    var eleClass = document.getElementsByClassName(arr[i]);
    [...eleClass].forEach((item, index) => {
      item.style.display = null;
      item.disabled = false;
    });
  }

  //同步解码模式、及模块菜单
  var visibleOptions = [...decodingType.options].filter(option =>
    option.style.display !== 'none' &&
    !option.hasAttribute('hidden') &&
    option.disabled === false
  );
  if (visibleOptions.length > 0) {
    decodingType.selectedIndex = visibleOptions[0].index;
  } else {
    decodingType.selectedIndex = -1; // 无可用选项时清除选择
  }
  var eleWasm = document.getElementsByClassName("decoderWasmModule");
  [...eleWasm].forEach(item => {
    item.style.display = decodingType.value == "0" ? null : "none";
	  item.disabled = decodingType.value == "0" ? false : true;;
  });

  //业务逻辑——播放速率
  var bIsStream = eleStreamType.selectedIndex == 0;
  let eleSpeed = document.getElementById("speed");
  eleSpeed.value = "1.0";
  var eleSpeedOpt = document.getElementsByClassName("speedOpt");
  [...eleSpeedOpt].forEach(item => {
    item.style.display = "none";
    item.disabled = true;
  });
  if (dataSpeed && !bIsStream) {
    let list = dataSpeed?.value?.split(",");
    [...list].forEach(item => {
      document.getElementsByClassName("speed" + item)[0].style.display = null;
      document.getElementsByClassName("speed" + item)[0].disabled = false;
    });
  } else {
    [...eleSpeedOpt].forEach(item => {
      item.style.display = null;
      item.disabled = false;
    });
  }

  if (dataSpeedDisabled && !bIsStream) {
    let list = dataSpeedDisabled?.value?.split(",");
    [...list].forEach(item => {
      document.getElementsByClassName("speed" + item)[0].style.display = "none";
      document.getElementsByClassName("speed" + item)[0].disabled = true;
    });
  }

  //业务逻辑——回放
  //devicePRI
  var elePri = document.getElementsByClassName("devicePreviewModule");
  var elePriLocal = document.getElementsByClassName("devicePlaybackModule");
  let timeTrack = document.getElementById('timeTrack');
  if (eleProtocol.value == "pri") {
    // 禁止拖动
    // timeTrack.disabled = true;
    [...elePri].forEach(item => { //预览模式，显示设备信息配置
      item.style.display = eleStreamType.selectedIndex == 0 ? null : "none";
      item.disabled = eleStreamType.selectedIndex == 0 ? false : true;
    });
	[...elePriLocal].forEach(item => { //回放模式
		item.style.display = eleStreamType.selectedIndex == 1 ? null : "none";
		item.disabled = eleStreamType.selectedIndex == 1 ? false : true;
	});
  } else {
    // 允许拖动
    timeTrack.disabled = false;
    [...elePri].forEach(item => {
      item.style.display = "none";
      item.disabled = true;
    });
	[...elePriLocal].forEach(item => {
		item.style.display = "none";
		item.disabled = true;
	});
  }

  //对讲通用
  var eleTalk = document.getElementsByClassName("talkModule");
  if (eleProtocol.value == "pri" || eleProtocol.value == "WebRTC") {
    [...eleTalk].forEach(item => { //预览模式，显示设备信息配置
      item.style.display = eleStreamType.selectedIndex == 0 ? null : "none";
      item.disabled = eleStreamType.selectedIndex == 0 ? false : true;
    });
  }

  //mp4
  var eleMP4 = document.getElementsByClassName("mp4PlaybackModule");
  if (eleProtocol.value == "mp4") {
    [...eleMP4].forEach(item => { //回放模式，显示mp4播放配置
      item.style.display = eleStreamType.selectedIndex == 1 ? null : "none";
      item.disabled = eleStreamType.selectedIndex == 1 ? false : true;
    });
  } else {
    [...eleMP4].forEach(item => {
      item.style.display = "none";
      item.disabled = true;
    });
  }

  //webRTC
  var eleWebRTC = document.getElementsByClassName("webRTCTalkModule");
  if (eleProtocol.value == "WebRTC") {
    [...eleWebRTC].forEach(item => { //对讲模式，显示webRTC配置
      item.style.display = eleStreamType.selectedIndex == 0 ? null : "none";
      item.disabled = eleStreamType.selectedIndex == 0 ? false : true;
    });

		//显示单向对讲配置
		onSelectWebRTCTalk_Module();
	} else {
		[...eleWebRTC].forEach(item => {
			item.style.display = "none";
			item.disabled = true;
		});
	}
}

//PRI协议选择播放模式（url/info）
const onSelectPRI_Module = function(type) {
	var elePriModule_url = document.getElementsByClassName("devicePreviewModule_children_url");
	var elePriModule_info = document.getElementsByClassName("devicePreviewModule_children_info");
	var elePriModuleLocal_url = document.getElementsByClassName("devicePlaybackModule_children_url");
	var elePriModuleLocal_info = document.getElementsByClassName("devicePlaybackModule_children_info");
	[...elePriModule_url].forEach(item => {
		item.style.display = "none";
		item.disabled = true;
	});
	[...elePriModule_info].forEach(item => {
		item.style.display = "none";
		item.disabled = true;
	});
	[...elePriModuleLocal_url].forEach(item => {
		item.style.display = "none";
		item.disabled = true;
	});
	[...elePriModuleLocal_info].forEach(item => {
		item.style.display = "none";
		item.disabled = true;
	});
	var priConfigEle = document.getElementById("priConfigModule");
	var priConfigEleLocal = document.getElementById("priConfigModule_local");
	var valueClass = priConfigEle.selectedOptions[0].attributes["data-decoder"].value;
	var valueClassLocal = priConfigEleLocal.selectedOptions[0].attributes["data-decoder"].value;
	let arr = valueClass.split(" ");
	let arrLocal = valueClassLocal.split(" ");
	var eleSpeedOpt = document.getElementsByClassName("speedOpt");
	let btnNextFrame = document.getElementById('btnNextFrame');
	if(type == 'preview'){
		isLocalFile = false;
		btnNextFrame.style.display = null;
		btnNextFrame.disabled = false;
		for (var i = 0; i < arr.length; i++) {
			var eleClass = document.getElementsByClassName(arr[i]);
			[...eleClass].forEach((item, index) => {
				item.style.display = null;
				item.disabled = false;
			});
		}

	}

	if(type == 'playback'){
		isLocalFile = priConfigEleLocal.value == 'local'? true:false; //是否本地文件
		btnNextFrame.style.display = isLocalFile ?'none': null;
		btnNextFrame.disabled = isLocalFile? true:false;
		[...eleSpeedOpt].forEach(item => {
			item.style.display = isLocalFile ? "none" :null;
			item.disabled = isLocalFile ? true : false;
		});
		let list = ['1.0'];
		[...list].forEach(item => {
			document.getElementsByClassName("speed" + item)[0].style.display = null;
			document.getElementsByClassName("speed" + item)[0].disabled = false;
		});
		for (var i = 0; i < arrLocal.length; i++) {
			var eleClass = document.getElementsByClassName(arrLocal[i]);
			[...eleClass].forEach((item, index) => {
				item.style.display = null;
				item.disabled = false;
			});
		}

	}

	//重置数据
	inputUrl.value = null;
	deviceIP.value = null;
	devicePort.value = null;
	deviceUsername.value = null;
	devicePassword.value = null;
	deviceChannel.value = null;
	deviceStream.value = "Main";
}

//MP4协议选择播放模式（url/localFile
const onSelectMP4_Module = function() {
	var eleMP4Module_url = document.getElementsByClassName("mp4PlaybackModule_children_url");
	var eleMP4Module_info = document.getElementsByClassName("mp4PlaybackModule_children_info");
	[...eleMP4Module_url].forEach(item => {
		item.style.display = "none";
		item.disabled = true;
	});
	[...eleMP4Module_info].forEach(item => {
		item.style.display = "none";
		item.disabled = true;
	});
	var mp4ConfigEle = document.getElementById("mp4ConfigModule");
	var valueClass = mp4ConfigEle.selectedOptions[0].attributes["data-decoder"].value;
	let arr = valueClass.split(" ");
	for (var i = 0; i < arr.length; i++) {
		var eleClass = document.getElementsByClassName(arr[i]);
		[...eleClass].forEach((item, index) => {
			item.style.display = null;
			item.disabled = false;
		});
	}

	//重置数据
	inputUrl.value = null;
	fileSelector.value = null;
}
	//WebRTC协议选择对讲模式
const onSelectWebRTCTalk_Module = function() {
	var eleWebRTCTalkModule_one = document.getElementsByClassName("webRTCTalkModule_children_oneTalk");
	var eleWebRTCTalkModule_two = document.getElementsByClassName("webRTCTalkModule_children_twoTalk");
	[...eleWebRTCTalkModule_one].forEach(item => {
		item.style.display = "none";
		item.disabled = true;
	});
	[...eleWebRTCTalkModule_two].forEach(item => {
		item.style.display = "none";
		item.disabled = true;
	});
	var webRTCTalkConfigEle = document.getElementById("webRTCTalkType");
	var valueClass = webRTCTalkConfigEle.selectedOptions[0].attributes["data-decoder"].value;
	let arr = valueClass.split(" ");
	for (var i = 0; i < arr.length; i++) {
		var eleClass = document.getElementsByClassName(arr[i]);
		[...eleClass].forEach((item, index) => {
			item.style.display = null;
			item.disabled = false;
		});
	}

	var eleTalk = document.getElementsByClassName("talkModule");
	[...eleTalk].forEach(item => { //预览模式，显示设备信息配置
		item.style.display = webRTCTalkConfigEle.selectedIndex == 0 ? null : "none";
		item.disabled = webRTCTalkConfigEle.selectedIndex == 0 ? false : true;
	});

	//重置数据
	webRTCTalkUrl.value = null;
}
//播放模式
const onSelectStreamType = function () {
  var eleStreamType = document.getElementById("streamType");
  var elePre = document.getElementsByClassName("previewModule");
  var eleBack = document.getElementsByClassName("playbackModule");
  [...elePre].forEach(item => {
    item.style.display = eleStreamType.selectedIndex == 0 ? null : "none";
	  item.disabled = eleStreamType.selectedIndex == 0 ? false : true;
  });
  [...eleBack].forEach(item => {
    item.style.display = eleStreamType.selectedIndex == 0 ? "none" : null;
	  item.disabled = eleStreamType.selectedIndex == 0 ? true : false;
  });


  //重置配置——值
  bufferTime.value = 2000; //缓冲时长
  lastFrame.value = true; //预览追帧
  previewReconn.value = false; //预览重连
  reconnNumber.value = -1; //重连次数
  reconnInterval.value = 5000; //重连间隔
  playbackReplay.value = false; //回放结束重播
  eleSpeed.value = "1.0"; //播放速率

  //重置显示
  //视频格式
  var visibleOptions_proto = [...protoList.options].filter(option =>
    option.style.display !== 'none' &&
    !option.hasAttribute('hidden') &&
    option.disabled === false
  );
  if (visibleOptions_proto.length > 0) {
    protoList.selectedIndex = visibleOptions_proto[0].index;
  } else {
    protoList.selectedIndex = -1; // 无可用选项时清除选择
  }
  onSelectProtocol();
  //解码模式
  var visibleOptions_decodType = [...decodingType.options].filter(option =>
    option.style.display !== 'none' &&
    !option.hasAttribute('hidden') &&
    option.disabled === false
  );
  if (visibleOptions_decodType.length > 0) {
    decodingType.selectedIndex = visibleOptions_decodType[0].index;
  } else {
    decodingType.selectedIndex = -1; // 无可用选项时清除选择
  }
  onSelectDecoder();
  //预览重连
  onSelectReconnType();

  //停止播放
  var currentState = self.player.fnGetState();
  if (currentState != emState_Idle) {
    stopVideo();
  }
}

//解码模式
const onSelectDecoder = function () {
  var currentState = self.player.fnGetState();
  if (currentState != emState_Idle) {
    stopVideo();
  }
  var eleWasm = document.getElementsByClassName("decoderWasmModule");
  [...eleWasm].forEach(item => {
    item.style.display = decodingType.value == "0" ? null : "none";
	  item.disabled = decodingType.value == "0" ? false : true;;
  });

  // 重置Canvas元素
  const canvas = document.getElementById('playCanvas');
  const newCanvas = resetCanvas(canvas);
}


//预览重连
const onSelectReconnType = function () {
  var eleReconnType = document.getElementById("previewReconn");

  var elePre = document.getElementsByClassName("reconnectModule");
  [...elePre].forEach(item => {
    item.style.display = eleReconnType.selectedIndex == 0 ? null : "none";
	  item.disabled = eleReconnType.selectedIndex == 0 ? false : true;
  });
}


//日志等级
const onSelectLogType = function (val) {
  let info = Number(val.value);
  self.player.updateLogLevel(info);
  logger.level = info;
  logger = new Logger("Page", self.player.options);
}

//根据配置项，选择渲染对象，硬解：video 软解：canvas
function onSelectDecoderRender() {
	var flag = false;
	var protoList = document.getElementById("protocol");
	var proto = protoList.options[protoList.selectedIndex].value;
	var eleStreamType = document.getElementById("streamType");
	if ((proto == "httpFlv" || proto == "http-wsFlv" || proto == "httpHls" || proto == "pri") || ((proto == "WebRTC") && eleStreamType.selectedIndex == 0)) {
		flag = true;
	}

  if (proto == "mp4") {
    flag = true;
  }
  var gwmModule = document.getElementsByClassName('gwmModule')[0];
  var flvModule = document.getElementsByClassName('flvModule')[0];

  //能力集获取
  var info = self.player.fnFeatureInfo();
  if (info) {
    if (proto == "httpFlv" || proto == "http-wsFlv" || proto == "pri") {
      flag = info.flvjsHEVC || false;
    }
    if (proto == "httpHls") {
      flag = info.hlsjsHEVC || false;
    }
  }

  if (flag) {
    gwmModule.style.display = "none";
	  gwmModule.disabled = true;
    flvModule.style.display = "block";
	  flvModule.disabled = false;
  } else {
    gwmModule.style.display = "block";
	  gwmModule.disabled = false;
    flvModule.style.display = "none";
	  flvModule.disabled = true;
  }
}

//设备码流类型
const onSelectDeviceStream = function() {

}
//播放速率
const onSelectSpeed = function () {
    var eleSpeed = document.getElementById("speed");
    self.player.fnSetSpeed(eleSpeed.value);
}

//时间跳转
function changeSkipTime(info) {
  self.player.fnPlayerSkipTime(info);
}

//拓展功能
//数字放大
const playZoom = function () {
  self.player.fnDigitZoom();
}

//截图
const playCapture = function () {
  let data = self.player.fnCapture();//自定义文件名称 ,必须携带文件后缀
}
//颜色--默认
const playSetColor = function () {
  self.player.fnSetDefaultColor();
  colorBrightnessTrack.value = self.player.colorBrightness;
  colorContrastTrack.value = self.player.colorContrast;
  colorHueTrack.value = self.player.colorHue;
  colorSaturationTrack.value = self.player.colorSaturation;
}

//语音对讲
const playVoice = function () {
  self.player.fnVoiceCollection();
}

//=================Tab切换=====================
// Tab切换功能实现


//==================控制台-日志打印========================
// 添加消息到控制台
function printMessage(data) {
  const consoleOutput = document.getElementById('consoleOutput');
  let timestamp = data?.time || new Date().toLocaleString();
  let type = data?.type;
  if (!type) {
    return;
  }
  let winId = data.winId;
  let module = data.module;
  let line = JSON.stringify(data.other);

  const messageElement = document.createElement('div');
  messageElement.className = 'console-message';

  messageElement.innerHTML = `
			        <div class="timestamp">${timestamp}</div>
			        <div class="message-content ${type}">[${winId}][${type}][${module}] ${line}</div>
			    `;

  consoleOutput.appendChild(messageElement, null);
  consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

// 清除控制台
const clearConsole = function () {
  while (consoleOutput.children.length > 0) {
    consoleOutput.removeChild(consoleOutput.firstChild);
  }

}

	//录播
const recoderDownload = function() {
  if (self.player) {
    self.player.fnRecoderDownload();//自定义文件名称，不用携带文件后缀
  }
}

//=================获取浏览器信息插件=======================
/**
 * 获取browser信息
 * @returns 
 */
async function fnBrowserInfo() {
    return await browser.getInfo();
  };

//右侧菜单——基本信息
//浏览器信息
async function baseInfo_browser() {
  let browserData = await fnBrowserInfo();
  // 定义键名的优先级顺序
  const priorityKeys = ["g711a",
    "browser", "browserVersion",
    "mseSupport", "webRTCSupport", "H264", "HEVC",
    "system", "systemVersion", "platform",
    "device", "screenWidth", "screenHeight",
    "clientWidth", "clientHeight",
    "network", "isOnline", "ip",
    "language", "timezone", "userAgent", "engine",
  ];
  // 1. 按优先级顺序输出
  const sortedOutput = {};
  priorityKeys.forEach(key => {
    if (browserData.hasOwnProperty(key)) {
      sortedOutput[key] = browserData[key];
    }
  });

  // 2. 收集剩余键并按字母顺序排序
  const otherKeys = Object.keys(browserData)
    .filter(key => !priorityKeys.includes(key))
    .sort();

  // 3. 添加剩余键值对
  otherKeys.forEach(key => {
    sortedOutput[key] = browserData[key];
  });

  const ouputDocm = document.getElementById('info3-tab');
  for (let [key, value] of Object.entries(sortedOutput)) {
    let info = value;
    if (typeof value === 'object' && value !== null) {
      info = JSON.stringify(value, null, 2)
    }
    let content = parseText(info);
    let type = "info";
    if (value == false) {
      type = "error";
    }

    //特殊翻译
    if (key == "HEVC") {
      key += "(H265)";
    }

    const messageElement = document.createElement('div');
    messageElement.className = 'console-message';
    messageElement.innerHTML = `
								    <div class="timestamp">${key}</div>
								    <div class="message-content ${type}">${content}</div>
								`;
    ouputDocm.insertBefore(messageElement, ouputDocm.lastElementChild);

  }
}
//右侧菜单——基础信息
//player能力集信息
function baseInfo_playFeature() {
  var result = self.player.fnFeatureInfo(); //获取能力集信息
  const ouputDocm = document.getElementById('info2-tab');
  for (let [key, value] of Object.entries(result)) {
    let content = "--";
    if (value != null) {
      content = parseText(value)
    }
    let type = "info";
    if (value == false) {
      type = "error";
    }
    const messageElement = document.createElement('div');
    messageElement.className = 'console-message';
    messageElement.innerHTML = `
				    <div class="timestamp">${key}</div>
				    <div class="message-content ${type}">${content}</div>
				`;
    ouputDocm.insertBefore(messageElement, ouputDocm.lastElementChild);

  }

}
//===============右侧菜单——动态信息====================
let setTimeout_DynamicData;

//tab页的动态数据--开始
function baseInfo_DynamicData_Start() {
  if (setTimeout_DynamicData) {
    clearTimeout(setTimeout_DynamicData);
  }
  let performanceData = fnDynamicData_Start();
  if (performanceData) {
    // 更新FPS信息
    document.getElementById('currentFps').textContent = performanceData.rendering.fps || 'unknown';
    document.getElementById('renderedFrames').textContent = performanceData.rendering.renderedFrames || 'unknown';
    document.getElementById('smoothness').textContent = performanceData.rendering.smoothness || '-';

    // 更新内存信息
    document.getElementById('usedMemory').textContent = performanceData.memory.usedMB || 'unknown';
    document.getElementById('totalMemory').textContent = performanceData.memory.totalMB || 'unknown';
    document.getElementById('memoryUsage').textContent = performanceData.memory.usagePercentage || 'unknown';

    // 更新CPU信息
    document.getElementById('cpuCores').textContent = performanceData.cpu.cores || 'unknown';
    document.getElementById('deviceMemory').textContent = navigator.deviceMemory || 'unknown';
    document.getElementById('batteryLevel').textContent = performanceData.device.batteryLevel ?
      Math.round(performanceData.device.batteryLevel) : 'unknown';

    // 更新网络信息
    document.getElementById('networkType').textContent = performanceData.network.type || 'unknown';
    document.getElementById('downlinkSpeed').textContent = performanceData.network.downlinkMbps ?
      performanceData.network.downlinkMbps.toFixed(1) : 'unknown';
    document.getElementById('networkRtt').textContent = performanceData.network.rttMs || 'unknown';

    // 更新长任务信息
    document.getElementById('longTasksCount').textContent = performanceData.longTasks.count || 'unknown';
    document.getElementById('lastLongTask').textContent = performanceData.longTasks.lastDuration ?
      performanceData.longTasks.lastDuration.toFixed(1) : 'unknown';
    document.getElementById('blockingTime').textContent = performanceData.longTasks.blockingTime ?
      performanceData.longTasks.blockingTime.toFixed(1) : 'unknown';

    // 更新渲染性能信息
    document.getElementById('fcpTime').textContent = performanceData.paint.fcp ?
      Math.round(performanceData.paint.fcp) : 'unknown';
    document.getElementById('lcpTime').textContent = performanceData.paint.lcp ?
      Math.round(performanceData.paint.lcp) : 'unknown';
  }

  //定时更新信息
  setTimeout_DynamicData = setTimeout(function() {
    baseInfo_DynamicData_Start();
  }, 3000);
}

//动态信息--停止
function baseInfo_DynamicData_Stop() {
  if (setTimeout_DynamicData) {
    clearTimeout(setTimeout_DynamicData);
  }
  fnDynamicData_Start();
}

var monitor;
/**
 * 动态信息--开始
 * @returns 
 */
function fnDynamicData_Start() {


	//停止动态参数监控
	fnDynamicData_Stop();

	if (!monitor) {
		// 创建监控实例
		monitor = new PerformanceMonitor();
		// 显示浏览器兼容性警告
		monitor.showCompatibilityWarnings();
		// 开始监控
		monitor.start();
	}

	//处理数据
	let data = monitor.getData();
	return data;

};

/**
 * 动态信息--停止
 */
function fnDynamicData_Stop() {
	monitor && monitor.reset();
	monitor = null;
};

//国际化业务
//设置语言
const onSelectLanguageType = function () {
  window.sessionStorage.setItem(langItem, langDocm.value);
  window.location.reload();
}

function initI18n(lang) {
  if (lang != 'en') {
    return;
  }
  // 翻译 HTML content
  document.querySelectorAll('[data-i18n]').forEach(el => {
    let text = el.dataset.i18n;
    if (el.textContent) {
      el.textContent = text;
    }
  });

  //翻译 title
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    let text = el.dataset.i18nTitle;
    if (el.attributes && el.attributes.title) {
      el.attributes.title.textContent = text;
    }
  });


}

			// ================弹框功能==========================
			window.showModal = function(data) {
				if (!data) {
					return;
				}
				let type = data.level;
				let errorCode = data.code;
				let errorMsg = data.msg;
				let errorUserCode = data.userCode;
				let errorUserMsg = data.userMsg;
				let errorAction = data.action;
				let errorCategory = data.category;
				let errorSource = data.source;

				if (!type || !errorCode) {
					return;
				}
				if (type != 'WARN' && type != 'ERROR') {
					return;
				}
				console.log("错误信息", "errorCode:", errorCode, "errorMsg:", errorMsg, "errorSource:", errorSource);
				const modal = document.getElementById('messageModal');

				const errorLevel = document.getElementById('errorLevel');
				const errorUserCodeEl = document.getElementById('errorUserCode');
				const errorUserMsgEl = document.getElementById('errorUserMsg');
				const errorActionEl = document.getElementById('errorAction');
				const errorCategoryEl = document.getElementById('errorCategory');

				// 设置错误信息
				errorLevel.textContent = type || '-';
				errorUserCodeEl.textContent = errorUserCode + `(response status:${errorCode})` || '-';
				errorUserMsgEl.textContent = errorUserMsg + `(response statusText:${errorMsg})` || '-';
				errorActionEl.textContent = errorAction || '-';
				errorCategoryEl.textContent = errorCategory || '-';

				// 显示弹框
				modal.style.display = 'flex';
			};



/*----------其他方法-----------*/
function parseBoolean(val) {
  let flag = val;
  switch (val) {
    case '1':
    case "true":
      flag = true;
      break;
    case '0':
    case "false":
      flag = false;
      break;
    default:
      break;
  }
  return flag;
}

function parseText(val) {
  let text = val;
  switch (val) {
    case 'true':
    case true:
      text = lang == 'en' ? "support" : "支持";
      break;
    case 'false':
    case false:
      text = lang == 'en' ? "not supported" : "不支持";
      break;
    default:
      break;
  }
  return text;

}

//重新渲染画板
function resetCanvas(canvas) {
  // 保存原始状态
  const originalWidth = canvas.width;
  const originalHeight = canvas.height;
  const originalStyle = canvas.style.cssText;
  const originalClass = canvas.className;
  const parent = canvas.parentNode;

  // 创建新Canvas元素
  const newCanvas = document.createElement('canvas');

  // 复制所有属性
  newCanvas.width = originalWidth;
  newCanvas.height = originalHeight;
  newCanvas.style.cssText = originalStyle;
  newCanvas.className = originalClass;
  newCanvas.id = canvas.id;

  // 替换DOM元素
  parent.replaceChild(newCanvas, canvas);

  return newCanvas;
}

function initLoad() {
  // 初始化代码
  console.log('初始化加载');
  initInfo()
  onSelectProtocol();
  onSelectStreamType();
  onSelectDecoder();
  onSelectReconnType();
  baseInfo_playFeature();
  baseInfo_browser();
  baseInfo_DynamicData_Start();
}

onMounted(() => {
  initLoad();
})



defineExpose({
  playVideo,
  stopVideo
})
</script>

<style></style>

// 性能监控工具类 (全面兼容Chrome/Edge/Firefox/Safari)
class PerformanceMonitor {
	constructor(options = {}) {
		// 配置选项
		this.options = {
			fpsInterval: 1000, // FPS更新间隔(毫秒)
			memoryInterval: 1000, // 内存更新间隔(毫秒)
			networkInterval: 2000, // 网络信息更新间隔(毫秒)
			...options
		};

		this.isMonitoring = false;
		this.intervals = {};
		this.lastFrameTime = 0;
		this.frameCount = 0;
		this.fps = 0;
		this.renderedFrames = 0;
		this.longTaskCount = 0;
		this.lastLongTaskDuration = 0;
		this.blockingTime = 0;
		this.fcp = null;
		this.lcp = null;
		this.batteryLevel = null;
		this.batteryCharging = false;

		// 数据存储
		this.performanceData = {
			memory: {
				totalMB: null,
				usedMB: null,
				availableMB: null,
				usagePercentage: null,
				supported: false
			},
			cpu: {
				cores: null,
				supported: false
			},
			network: {
				type: null,
				downlinkMbps: null,
				rttMs: null,
				supported: false
			},
			rendering: {
				fps: null,
				renderedFrames: null,
				smoothness: null,
				lastUpdated: null
			},
			longTasks: {
				count: 0,
				lastDuration: 0,
				blockingTime: 0,
				supported: false
			},
			paint: {
				fcp: null,
				lcp: null,
				supported: false
			},
			device: {
				batteryLevel: null,
				charging: null,
				supported: false
			},
			resources: {
				scriptLoadTime: 0,
				imageLoadTime: 0,
				count: 0,
				supported: false
			},
			timestamp: null
		};

		// 图表数据
		this.chartData = {
			fps: [],
			memory: []
		};

		this.initStaticInfo();
	}

	// 初始化静态信息（全面兼容Firefox）
	initStaticInfo() {
		try {
			// 设备内存（仅Chrome/Edge支持）
			this.performanceData.memory.supported = !!(window.performance && performance.memory);

			// CPU核心数（Firefox支持）
			if (navigator.hardwareConcurrency) {
				this.performanceData.cpu.cores = navigator.hardwareConcurrency;
				this.performanceData.cpu.supported = true;
			}

			// 网络API支持检测（Firefox部分支持）
			this.performanceData.network.supported = this.isNetworkApiSupported();

			// 长任务监控支持（Firefox不支持）
			this.performanceData.longTasks.supported = this.isLongTaskSupported();

			// 渲染性能监控（Firefox部分支持）
			this.performanceData.paint.supported = this.isPaintObserverSupported();
			if (this.performanceData.paint.supported) {
				this.setupPaintObserver();
			}

			// 电池信息（Firefox不支持）
			this.performanceData.device.supported = this.isBatteryApiSupported();
			if (this.performanceData.device.supported) {
				this.updateBatteryInfo();
			}

			// 资源加载（Firefox支持但跨域资源受限）
			this.performanceData.resources.supported = this.isResourceTimingSupported();

			// Firefox特殊处理：添加FCP模拟
			if (!this.performanceData.paint.supported) {
				this.simulateFCPForFirefox();
			}
		} catch (error) {
			console.error('PerformanceMonitor initialization error:', error);
		}
	}

	// Firefox兼容性：网络API支持检测
	isNetworkApiSupported() {
		// Firefox支持但属性不同
		if ('connection' in navigator) {
			const conn = navigator.connection;
			// Firefox没有effectiveType但有type
			return conn && (conn.effectiveType !== undefined || conn.type !== undefined);
		}
		return false;
	}

	// Firefox兼容性：长任务检测
	isLongTaskSupported() {
		// Firefox目前不支持longtask
		if (typeof PerformanceObserver === 'undefined') return false;

		// 安全检测supportedEntryTypes
		const supported = PerformanceObserver.supportedEntryTypes;
		return supported && supported.includes('longtask');
	}

	// Firefox兼容性：渲染性能监控
	isPaintObserverSupported() {
		// Firefox 58+支持paint
		if (typeof PerformanceObserver === 'undefined') return false;

		const supported = PerformanceObserver.supportedEntryTypes;
		return supported && supported.includes('paint');
	}

	// Firefox兼容性：电池API
	isBatteryApiSupported() {
		// Firefox移动版支持，桌面版已弃用
		return 'getBattery' in navigator &&
			typeof navigator.getBattery === 'function';
	}

	// Firefox兼容性：资源计时
	isResourceTimingSupported() {
		return !!(window.performance &&
			performance.getEntriesByType &&
			typeof performance.getEntriesByType === 'function');
	}

	// Firefox兼容性：模拟FCP
	simulateFCPForFirefox() {
		if (document.readyState === 'complete') {
			this.fcp = performance.now();
			this.performanceData.paint.fcp = this.fcp;
			return;
		}

		const onContentLoaded = () => {
			this.fcp = performance.now();
			this.performanceData.paint.fcp = this.fcp;
			document.removeEventListener('DOMContentLoaded', onContentLoaded);
		};

		document.addEventListener('DOMContentLoaded', onContentLoaded);
	}

	// 设置渲染性能监控（Firefox兼容）
	setupPaintObserver() {
		try {
			const observer = new PerformanceObserver((list) => {
				const entries = list.getEntries();
				for (const entry of entries) {
					if (entry.name === 'first-contentful-paint') {
						this.fcp = entry.startTime;
						this.performanceData.paint.fcp = this.fcp;
					} else if (entry.name === 'largest-contentful-paint') {
						this.lcp = entry.startTime;
						this.performanceData.paint.lcp = this.lcp;
					}
				}
			});

			observer.observe({
				type: 'paint',
				buffered: true
			});
		} catch (e) {
			console.error('Paint observer setup failed:', e);
			this.performanceData.paint.supported = false;
		}
	}

	// 更新电池信息（Firefox兼容）
	updateBatteryInfo() {
		if (!this.performanceData.device.supported) return;

		navigator.getBattery().then(battery => {
			this.batteryLevel = battery.level * 100;
			this.batteryCharging = battery.charging;

			this.performanceData.device.batteryLevel = this.batteryLevel;
			this.performanceData.device.charging = this.batteryCharging;

			// 监听电池状态变化
			const updateBattery = () => {
				this.batteryLevel = battery.level * 100;
				this.batteryCharging = battery.charging;
				this.performanceData.device.batteryLevel = this.batteryLevel;
				this.performanceData.device.charging = this.batteryCharging;
			};

			battery.addEventListener('levelchange', updateBattery);
			battery.addEventListener('chargingchange', updateBattery);
		}).catch(e => {
			console.error('Battery API not supported:', e);
			this.performanceData.device.supported = false;
		});
	}

	// 设置长任务监控（Firefox兼容）
	setupLongTaskObserver() {
		if (!this.performanceData.longTasks.supported) return;

		try {
			this.longTaskObserver = new PerformanceObserver(list => {
				const entries = list.getEntries();
				this.longTaskCount += entries.length;

				if (entries.length > 0) {
					this.lastLongTaskDuration = entries[entries.length - 1].duration;
					this.blockingTime += entries.reduce((sum, entry) => sum + entry.duration, 0);
				}

				this.performanceData.longTasks.count = this.longTaskCount;
				this.performanceData.longTasks.lastDuration = this.lastLongTaskDuration;
				this.performanceData.longTasks.blockingTime = this.blockingTime;
			});

			this.longTaskObserver.observe({
				type: 'longtask',
				buffered: true
			});
		} catch (e) {
			console.error('Long task observer setup failed:', e);
			this.performanceData.longTasks.supported = false;
		}
	}

	// 更新资源加载信息（Firefox兼容）
	updateResourceInfo() {
		if (!this.performanceData.resources.supported) return;

		try {
			const resources = performance.getEntriesByType('resource');
			let scriptLoadTime = 0;
			let imageLoadTime = 0;
			let scriptCount = 0;
			let imageCount = 0;

			for (const res of resources) {
				if (res.initiatorType === 'script') {
					scriptLoadTime += res.duration;
					scriptCount++;
				} else if (res.initiatorType === 'img') {
					imageLoadTime += res.duration;
					imageCount++;
				}
			}

			// 计算平均值避免总值无限增长
			this.performanceData.resources.scriptLoadTime = scriptCount > 0 ?
				scriptLoadTime / scriptCount : 0;
			this.performanceData.resources.imageLoadTime = imageCount > 0 ?
				imageLoadTime / imageCount : 0;
			this.performanceData.resources.count = resources.length;
		} catch (e) {
			console.warn('Resource timing restricted (cross-origin):', e);
			this.performanceData.resources.supported = false;
		}
	}

	// 开始监控（Firefox兼容）
	start() {
		if (this.isMonitoring) return;

		this.isMonitoring = true;
		this.lastFrameTime = performance.now();
		this.frameCount = 0;
		this.renderedFrames = 0;
		this.longTaskCount = 0;
		this.lastLongTaskDuration = 0;
		this.blockingTime = 0;

		// 开始FPS监控
		this.monitorFPS();

		// 设置长任务监控
		if (this.performanceData.longTasks.supported) {
			this.setupLongTaskObserver();
		}

		// 设置定时监控任务
		this.setupIntervals();
	}

	// 设置定时监控任务（Firefox兼容）
	setupIntervals() {
		// 内存监控（仅Chrome/Edge）
		if (this.performanceData.memory.supported) {
			this.updateMemoryInfo();
			this.intervals.memory = setInterval(() => {
				this.updateMemoryInfo();
			}, this.options.memoryInterval);
		}

		// 网络监控（Firefox部分支持）
		if (this.performanceData.network.supported) {
			this.updateNetworkInfo();
			this.intervals.network = setInterval(() => {
				this.updateNetworkInfo();
			}, this.options.networkInterval);
		}

		// FPS信息更新（所有浏览器支持）
		this.updateFPSInfo();
		this.intervals.fps = setInterval(() => {
			this.updateFPSInfo();
		}, this.options.fpsInterval);

		// 资源信息更新（Firefox支持）
		if (this.performanceData.resources.supported) {
			this.updateResourceInfo();
			this.intervals.resources = setInterval(() => {
				this.updateResourceInfo();
			}, 5000);
		}
	}

	// 停止监控
	stop() {
		if (!this.isMonitoring) return;

		this.isMonitoring = false;

		// 清除所有定时器
		for (const key in this.intervals) {
			clearInterval(this.intervals[key]);
		}
		this.intervals = {};

		// 停止长任务监控
		if (this.longTaskObserver) {
			this.longTaskObserver.disconnect();
		}
	}

	// 重置数据
	reset() {
		this.stop();
		this.renderedFrames = 0;
		this.longTaskCount = 0;
		this.lastLongTaskDuration = 0;
		this.blockingTime = 0;
		this.fcp = null;
		this.lcp = null;
		this.chartData.fps = [];
		this.chartData.memory = [];

		// 保留支持状态和静态信息
		this.performanceData = {
			...this.performanceData,
			memory: {
				...this.performanceData.memory,
				usedMB: null,
				availableMB: null,
				usagePercentage: null
			},
			network: {
				...this.performanceData.network,
				type: null,
				downlinkMbps: null,
				rttMs: null
			},
			rendering: {
				fps: null,
				renderedFrames: null,
				smoothness: null,
				lastUpdated: null
			},
			longTasks: {
				...this.performanceData.longTasks,
				count: 0,
				lastDuration: 0,
				blockingTime: 0
			},
			paint: {
				...this.performanceData.paint,
				fcp: null,
				lcp: null
			},
			resources: {
				...this.performanceData.resources,
				scriptLoadTime: 0,
				imageLoadTime: 0,
				count: 0
			},
			timestamp: null
		};
	}

	// 监控帧率(FPS)（Firefox兼容）
	monitorFPS() {
		if (!this.isMonitoring) return;

		const now = performance.now();
		this.frameCount++;
		this.renderedFrames++;

		const delta = now - this.lastFrameTime;
		if (delta >= 1000) {
			this.fps = Math.round((this.frameCount * 1000) / delta);
			this.lastFrameTime = now;
			this.frameCount = 0;
		}

		requestAnimationFrame(() => this.monitorFPS());
	}

	// 更新内存信息（仅Chrome/Edge）
	updateMemoryInfo() {
		try {
			// Firefox安全处理
			if (!performance || !performance.memory) {
				this.performanceData.memory.supported = false;
				return;
			}

			const mem = performance.memory;
			const usedMB = Math.round(mem.usedJSHeapSize / (1024 * 1024));
			const totalMB = Math.round(mem.totalJSHeapSize / (1024 * 1024));
			const limitMB = Math.round(mem.jsHeapSizeLimit / (1024 * 1024));
			const availableMB = Math.max(0, limitMB - usedMB);
			const usagePercentage = Math.min(100, Math.round((mem.usedJSHeapSize / mem.jsHeapSizeLimit) * 100));

			this.performanceData.memory = {
				...this.performanceData.memory,
				totalMB: limitMB,
				usedMB,
				availableMB,
				usagePercentage
			};

			// 更新图表数据
			this.chartData.memory.push({
				x: Date.now(),
				y: usedMB
			});

			// 仅保留最近50个数据点
			if (this.chartData.memory.length > 50) {
				this.chartData.memory.shift();
			}
		} catch (error) {
			console.error('Memory update failed (Chrome/Edge only):', error);
			this.performanceData.memory.supported = false;
		}
	}

	// 更新网络信息（Firefox兼容）
	updateNetworkInfo() {
		try {
			// Firefox安全处理
			if (!navigator.connection) {
				this.performanceData.network.supported = false;
				return;
			}

			const conn = navigator.connection;
			let networkType = null;

			// Firefox兼容处理
			if (conn.effectiveType) {
				networkType = conn.effectiveType;
			} else if (conn.type) {
				// 映射Firefox类型到标准类型
				const typeMap = {
					'wifi': 'wifi',
					'cellular': 'cellular',
					'ethernet': 'ethernet',
					'bluetooth': 'bluetooth',
					'wimax': '4g',
					'other': 'unknown',
					'none': 'offline'
				};
				networkType = typeMap[conn.type] || conn.type;
			}

			this.performanceData.network = {
				...this.performanceData.network,
				type: networkType,
				downlinkMbps: conn.downlink || null,
				rttMs: conn.rtt || null
			};
		} catch (error) {
			console.error('Network update error:', error);
			this.performanceData.network.supported = false;
		}
	}

	// 更新FPS信息
	updateFPSInfo() {
		// 计算播放流畅度
		let smoothness = 'smooth';
		if (this.fps < 20) smoothness = 'stuttering';
		else if (this.fps < 30) smoothness = 'choppy';
		else if (this.fps < 45) smoothness = 'medium';

		this.performanceData.rendering = {
			fps: this.fps,
			renderedFrames: this.renderedFrames,
			smoothness,
			lastUpdated: Date.now()
		};

		this.performanceData.timestamp = new Date().toISOString();

		// 更新图表数据
		this.chartData.fps.push({
			x: Date.now(),
			y: this.fps
		});

		// 仅保留最近50个数据点
		if (this.chartData.fps.length > 50) {
			this.chartData.fps.shift();
		}
	}

	// 获取当前性能数据
	getData() {
		return {
			...this.performanceData,
			// 添加元数据
			meta: {
				isMonitoring: this.isMonitoring,
				timestamp: Date.now(),
				userAgent: navigator.userAgent
			}
		};
	}

	// 检查功能支持（Firefox兼容）
	supports() {
		return {
			memory: this.performanceData.memory.supported,
			network: this.performanceData.network.supported,
			cpu: this.performanceData.cpu.supported,
			fps: true, // 始终支持FPS
			longTasks: this.performanceData.longTasks.supported,
			paint: this.performanceData.paint.supported,
			battery: this.performanceData.device.supported,
			resources: this.performanceData.resources.supported
		};
	}

	// 显示浏览器兼容性警告
	showCompatibilityWarnings() {
		const supports = this.supports();
		const ua = navigator.userAgent.toLowerCase();
		const isFirefox = ua.includes('firefox');

		if (isFirefox) {
			if (!supports.memory) console.warn('Firefox: 内存监控仅支持Chrome/Edge浏览器');
			if (!supports.longTasks) console.warn('Firefox: 长任务监控不可用');
			if (!supports.battery) console.warn('Firefox: 电池API仅在移动设备支持');
		}
		
	}
}

export default PerformanceMonitor;
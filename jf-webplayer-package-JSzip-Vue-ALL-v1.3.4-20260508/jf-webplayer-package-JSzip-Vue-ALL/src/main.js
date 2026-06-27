import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
// 全局注册
import Antd from 'ant-design-vue';

import VConsole from 'vconsole';
const vConsole = new VConsole();

const app = createApp(App)
app.use(Antd);
app.mount('#app');

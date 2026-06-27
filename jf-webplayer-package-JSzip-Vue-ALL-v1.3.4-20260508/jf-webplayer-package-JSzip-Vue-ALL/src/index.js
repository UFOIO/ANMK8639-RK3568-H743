import JFPlayer from './components/jfplayer/index.vue'

export default {
    install(app) {
        app.component('JFPlayer',JFPlayer)
    }
}

export {
    JFPlayer
}
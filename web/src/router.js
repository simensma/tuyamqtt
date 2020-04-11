import Vue from 'vue'
import Router from 'vue-router'
import Home from './views/home.vue'
import SettingList from '@/views/settinglist.vue'
import SettingDetail from '@/views/settingdetail.vue'
import EntityList from '@/views/entitylist.vue'
import EntityDetail from '@/views/entitydetail.vue'

Vue.use(Router)

export default new Router({
  mode: 'history',
  base: process.env.BASE_URL,
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home
    },
    {
      path: '/settings',
      name: 'settinglist',
      component: SettingList
    },
    {
      path: '/settings/:id',
      name: 'settingdetail',
      component: SettingDetail
    },
    {
      path: '/entities',
      name: 'entitylist',
      component: EntityList
    },
    {
      path: '/entities/:id',
      name: 'entitydetail',
      component: EntityDetail
    },
  ]
})

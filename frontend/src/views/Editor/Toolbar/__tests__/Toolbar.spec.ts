import { createPinia, setActivePinia } from 'pinia'
import { shallowMount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { beforeEach, describe, expect, it } from 'vitest'

import { useMainStore } from '@/store'
import { ToolbarStates } from '@/types/toolbar'
import Toolbar from '../index.vue'
import SlideDesignPanel from '../SlideDesignPanel/index.vue'

describe('Editor Toolbar', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('首次进入未选中元素的编辑器时自动显示幻灯片设计面板', async () => {
    const mainStore = useMainStore()

    // 模拟从“元素样式”状态离开编辑器后，再进入一个没有选中元素的作品。
    mainStore.setToolbarState(ToolbarStates.EL_STYLE)
    mainStore.setActiveElementIdList([])

    const wrapper = shallowMount(Toolbar)
    await nextTick()

    // 页签与内容面板必须保持一致，避免出现只有页签、下方内容空白的状态。
    expect(mainStore.toolbarState).toBe(ToolbarStates.SLIDE_DESIGN)
    expect(wrapper.findComponent(SlideDesignPanel).exists()).toBe(true)
  })
})

/** 与 PostLoginOnboarding.vue 配套的默认三步题目 */
export const DEFAULT_POST_LOGIN_ONBOARDING_QUESTIONS = [
  {
    title: '你学习钢琴多久了？',
    options: [
      { id: 'dur_never', label: '从未学过' },
      { id: 'dur_lt6m', label: '少于6个月' },
      { id: 'dur_6m_2y', label: '6个月–2年' },
      { id: 'dur_gt2y', label: '2年以上' },
    ],
  },
  {
    title: '你目前能演奏的难度？',
    options: [
      { id: 'play_one_hand', label: '单手简单旋律' },
      { id: 'play_two_simple', label: '双手简单配合' },
      { id: 'play_full_simple', label: '可以弹完整简单曲子' },
      { id: 'play_medium', label: '可以弹中等难度曲子' },
    ],
  },
  {
    title: '你平时练琴频率是？',
    options: [
      { id: 'freq_rare', label: '几乎不练' },
      { id: 'freq_1_2', label: '每周1–2次' },
      { id: 'freq_3_5', label: '每周3–5次' },
      { id: 'freq_daily', label: '几乎每天练习' },
    ],
  },
]

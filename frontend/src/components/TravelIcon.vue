<script setup>
defineProps({
  name: { type: String, required: true },
  size: { type: Number, default: 44 },
})
</script>

<!-- Illustrated travel icons, drawn inline so the page needs no image files. -->
<template>
  <svg :width="size" :height="size" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
    <template v-if="name === 'stays'">
      <rect x="6" y="22" width="36" height="12" rx="3" fill="#3c5a99" />
      <rect x="9" y="15" width="12" height="9" rx="3" fill="#dfe8f7" />
      <rect x="23" y="15" width="16" height="9" rx="3" fill="#dfe8f7" />
      <rect x="6" y="33" width="4" height="7" rx="1.5" fill="#23355e" />
      <rect x="38" y="33" width="4" height="7" rx="1.5" fill="#23355e" />
    </template>

    <template v-else-if="name === 'flights'">
      <path d="M24 5l4 15 14 8v4l-14-4-1 10 5 4v3l-8-3-8 3v-3l5-4-1-10-14 4v-4l14-8z" fill="#3c5a99" />
      <path d="M24 5l4 15-4 1z" fill="#6c8fd6" />
    </template>

    <template v-else-if="name === 'cars'">
      <path d="M9 24l4-9h22l4 9v11H9z" fill="#3c5a99" />
      <path d="M15 17h18l3 7H12z" fill="#dfe8f7" />
      <circle cx="16" cy="35" r="4" fill="#23355e" />
      <circle cx="32" cy="35" r="4" fill="#23355e" />
      <rect x="11" y="27" width="5" height="3" rx="1" fill="#ffc72c" />
      <rect x="32" y="27" width="5" height="3" rx="1" fill="#ffc72c" />
    </template>

    <template v-else-if="name === 'packages'">
      <rect x="7" y="26" width="26" height="10" rx="2.5" fill="#3c5a99" />
      <rect x="10" y="21" width="9" height="7" rx="2" fill="#dfe8f7" />
      <path d="M31 8l2.5 8 8 4v2.5l-8-2-.5 6 3 2v2l-5-2-5 2v-2l3-2-.5-6-8 2V20l8-4z" fill="#6c8fd6" />
    </template>

    <template v-else-if="name === 'activities'">
      <path d="M8 22c0-8 7.5-14 16-14s16 6 16 14z" fill="#e8734a" />
      <path d="M8 22c0-8 7.5-14 16-14-4 3-6 8-6 14z" fill="#f29a73" />
      <rect x="23" y="21" width="2.5" height="18" fill="#23355e" />
      <rect x="10" y="38" width="28" height="3" rx="1.5" fill="#ffc72c" />
    </template>

    <template v-else-if="name === 'cruises'">
      <path d="M6 30h36l-5 9H11z" fill="#3c5a99" />
      <rect x="13" y="22" width="22" height="8" rx="1.5" fill="#dfe8f7" />
      <rect x="18" y="15" width="12" height="7" rx="1.5" fill="#6c8fd6" />
      <rect x="22" y="9" width="4" height="6" fill="#e8734a" />
      <path d="M4 42c4 0 4-2 8-2s4 2 8 2 4-2 8-2 4 2 8 2 4-2 8-2" stroke="#6c8fd6" stroke-width="2" fill="none" />
    </template>

    <template v-else-if="name === 'external'">
      <path d="M28 8h12v12M40 8L22 26M36 28v10a2 2 0 01-2 2H10a2 2 0 01-2-2V14a2 2 0 012-2h10" stroke="currentColor" stroke-width="3.5" fill="none" stroke-linecap="round" stroke-linejoin="round" />
    </template>
  </svg>
</template>

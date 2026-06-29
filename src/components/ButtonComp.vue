<script setup>
defineProps({
  label: { type: String, default: 'Click me' },
  variant: { type: String, default: 'primary' },
  disabled: { type: Boolean, default: false },
})

defineEmits(['click'])
</script>

<template>
  <button
    :class="`btn btn-${variant}`"
    :disabled="disabled"
    @click="$emit('click')"
  >
    <slot>{{ label }}</slot>
  </button>
</template>

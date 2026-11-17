const EDITABLE_SELECTOR = 'textarea, input:not([type="hidden"]):not([type="button"]):not([type="submit"]):not([type="reset"]):not([type="checkbox"]):not([type="radio"]):not([type="file"]):not([type="range"]):not([type="color"]), [contenteditable="true"]';
let lastEditable = null;

document.addEventListener('focusin', (event) => {
  if (isEditable(event.target)) lastEditable = event.target;
}, true);

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== 'speech-prompt-insert') return;
  const target = getTarget();
  sendResponse({ ok: !!target && insertText(target, message.text) });
});

function getTarget() {
  const active = document.activeElement;
  if (isEditable(active)) {
    lastEditable = active;
    return active;
  }
  return isEditable(lastEditable) ? lastEditable : null;
}

function isEditable(element) {
  return element instanceof HTMLElement && element.matches(EDITABLE_SELECTOR)
    && !element.disabled && !element.readOnly
    && (element.isContentEditable || element.matches('input, textarea'));
}

function insertText(element, text) {
  if (!text) return false;
  element.focus();
  if (element.matches('input, textarea')) {
    const start = element.selectionStart ?? element.value.length;
    const end = element.selectionEnd ?? start;
    const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(prototype, 'value')?.set?.call(element, element.value.slice(0, start) + text + element.value.slice(end));
    element.setSelectionRange(start + text.length, start + text.length);
  } else {
    const selection = window.getSelection();
    const range = selection?.rangeCount ? selection.getRangeAt(0) : document.createRange();
    if (!element.contains(range.commonAncestorContainer)) { range.selectNodeContents(element); range.collapse(false); }
    range.deleteContents();
    const node = document.createTextNode(text);
    range.insertNode(node); range.setStartAfter(node); range.collapse(true);
    selection.removeAllRanges(); selection.addRange(range);
  }
  element.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: text }));
  element.dispatchEvent(new Event('change', { bubbles: true }));
  return true;
}

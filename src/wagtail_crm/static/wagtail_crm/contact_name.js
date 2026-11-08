(() => {
  // Match Python str.strip(), including NEL and excluding BOM.
  const nonempty = value => /[^\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]/u.test(value);
  const normalized = value => value.replace(/\r\n?/g, '\n');
  function setup(editor) {
    if (editor.dataset.ready) return;
    editor.dataset.ready = 'true';
    const mode = editor.querySelector('[data-name-mode]');
    const parts = editor.querySelector('[data-name-parts]');
    const full = editor.querySelector('[data-full-name]');
    const join = editor.querySelector('[data-name-separator]');
    const preview = editor.querySelector('[data-name-preview]');
    const originals = new WeakMap();
    const errors = editor.closest('[data-field]')?.querySelector('[data-field-errors]');
    if (editor.getAttribute('aria-invalid') === 'true' && errors && !errors.id) errors.id = `${editor.dataset.fieldId}_error`;
    const initial = JSON.parse(editor.querySelector('script[type="application/json"]').textContent);
    function remember(control, value) { control.value = value; originals.set(control, value); }
    function text(control) {
      const original = originals.get(control);
      return original !== undefined && control.value === normalized(original) ? original : control.value;
    }
    remember(full, initial.full);
    remember(join, initial.separator);
    [...parts.children].forEach((row, index) => remember(row.querySelector('[data-part-value]'), initial.values[index] || ''));
    function state() {
      return {mode: mode.value, full: text(full), separator: text(join),
        kinds: [...parts.children].map(row => row.querySelector('[data-part-kind]').value),
        values: [...parts.children].map(row => text(row.querySelector('[data-part-value]')))};
    }
    function partsState() { const {kinds, values, separator} = state(); return JSON.stringify({kinds, values, separator}); }
    let lastGeneratedParts = null;
    let generated = '', invalid = true;
    mode.hidden = true;
    editor.querySelector('[data-mode-label]').hidden = true;
    editor.querySelector('[data-toggle-name]').hidden = false;
    function update() {
      const structured = mode.value === 'structured';
      const fieldId = editor.dataset.fieldId;
      editor.id = structured ? fieldId : `${fieldId}_editor`;
      full.id = structured ? `${fieldId}_full` : fieldId;
      editor.querySelector('[data-toggle-name]').textContent = structured ? 'Use a full name' : 'Enter name parts';
      editor.querySelector('[data-supplied]').hidden = structured;
      editor.querySelector('[data-structured]').hidden = !structured;
      generated = ''; invalid = false;
      let previousSeparator = true;
      const rows = [...parts.children];
      rows.forEach((row, index) => {
        row.querySelector('[data-part-label]').textContent = `Name part ${index + 1}`;
        const kind = row.querySelector('[data-part-kind]').value;
        const separator = kind === 'separator';
        const value = text(row.querySelector('[data-part-value]'));
        if (!['given', 'surname', 'surname2', 'separator'].includes(kind) || separator && previousSeparator || !separator && !nonempty(value)) invalid = true;
        if (index && !separator && !previousSeparator) generated += text(join);
        generated += value;
        previousSeparator = separator;
        const disabled = mode.disabled;
        row.querySelector('[data-move-up]').disabled = disabled || index === 0;
        row.querySelector('[data-move-down]').disabled = disabled || index === rows.length - 1;
      });
      invalid ||= !rows.length || previousSeparator;
      preview.value = generated;
      editor.querySelector('[data-name-preview-error]').textContent = invalid ? 'Enter name parts with separators only between parts.' : '';
      editor.querySelector('[data-name-payload]').value = JSON.stringify(state());
    }
    editor.addEventListener('input', update);
    editor.addEventListener('change', update);
    editor.closest('form')?.addEventListener('submit', update);
    document.querySelectorAll('label').forEach(label => {
      if (label.htmlFor === editor.dataset.fieldId) label.addEventListener('click', () => {
        if (mode.value === 'structured') editor.focus();
      });
    });
    editor.addEventListener('click', event => {
      const button = event.target.closest('button');
      if (!button || button.disabled) return;
      const row = button.closest('[data-name-part]');
      let moved = false;
      if (button.hasAttribute('data-toggle-name')) {
        if (mode.value === 'structured') {
          if (!invalid && lastGeneratedParts !== partsState()) {
            remember(full, generated);
            lastGeneratedParts = partsState();
          }
          mode.value = 'supplied';
        } else mode.value = 'structured';
      } else if (button.hasAttribute('data-add-part')) {
        parts.append(editor.querySelector('[data-part-template]').content.cloneNode(true));
        parts.lastElementChild.querySelector('[data-part-value]').focus();
      } else if (button.hasAttribute('data-remove-part')) {
        const focusRow = row.nextElementSibling || row.previousElementSibling;
        row.remove();
        (focusRow?.querySelector('[data-part-value]') || editor.querySelector('[data-add-part]')).focus();
      } else if (button.hasAttribute('data-move-up') && row.previousElementSibling) {
        parts.insertBefore(row, row.previousElementSibling); moved = true;
      } else if (button.hasAttribute('data-move-down') && row.nextElementSibling) {
        parts.insertBefore(row.nextElementSibling, row); moved = true;
      }
      update();
      if (moved) row.querySelector('[data-part-value]').focus();
    });
    editor.querySelector('[data-add-part]').disabled = mode.disabled;
    update();
  }
  function initialize() { document.querySelectorAll('[data-contact-name]').forEach(setup); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize);
  else initialize();
})();

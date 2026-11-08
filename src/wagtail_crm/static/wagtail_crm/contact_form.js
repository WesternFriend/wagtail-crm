/* The existing kind selector controls only which ordinary name fields apply. */
(() => {
  const init = () => {
    const kind = document.getElementById('id_kind');
    if (!kind) return;
    const show = () => {
      const organization = kind.value === 'organization';
      for (const [id, visible] of [
        ['id_given_name', !organization],
        ['id_surname', !organization],
        ['id_organization_name', organization],
      ]) {
        const input = document.getElementById(id);
        const panel = input?.closest('[data-field-wrapper]') || input?.closest('[data-field]');
        if (panel) panel.hidden = !visible;
        if (input) input.disabled = !visible;
      }
    };
    kind.addEventListener('change', show);
    show();
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();

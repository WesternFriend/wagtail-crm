/* Show only the ordinary name fields applicable to this contact. */
(() => {
  const init = () => {
    const kind = document.getElementById('id_kind');
    const given = document.getElementById('id_given_name');
    if (!kind) return;
    const show = () => {
      const organization = kind.value === 'organization';
      for (const [id, visible] of [
        ['id_given_name', !organization],
        ['id_family_name', !organization],
        ['id_name', organization || !given],
      ]) {
        const input = document.getElementById(id);
        const panel = input?.closest('[data-field-wrapper]');
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

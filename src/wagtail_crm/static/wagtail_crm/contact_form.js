/* The existing kind selector controls only which ordinary name fields apply. */
(() => {
  const init = () => {
    const kind = document.getElementById('id_kind');
    if (!kind) return;
    const given = document.getElementById('id_given_name');
    const surname = document.getElementById('id_surname');
    const full = document.getElementById('id_full_name');
    const organizationName = document.getElementById('id_organization_name');
    let personEdited = false;
    let organizationEdited = false;
    for (const input of [given, surname, full]) {
      input?.addEventListener('input', () => { personEdited = true; });
    }
    organizationName?.addEventListener('input', () => { organizationEdited = true; });
    const changeType = () => {
      if (kind.value === 'organization' && !organizationEdited && personEdited) {
        organizationName.value = full ? full.value : [given?.value, surname?.value].filter(value => value?.trim()).join(' ');
      } else if (kind.value === 'person' && full && !personEdited && organizationEdited) {
        full.value = organizationName.value;
      }
      show();
    };
    const show = () => {
      const organization = kind.value === 'organization';
      for (const [id, visible] of [
        ['id_given_name', !organization],
        ['id_surname', !organization],
        ['id_full_name', !organization],
        ['id_organization_name', organization],
      ]) {
        const input = document.getElementById(id);
        const panel = input?.closest('[data-field-wrapper]') || input?.closest('[data-field]');
        if (panel) panel.hidden = !visible;
        if (input) input.disabled = !visible;
      }
    };
    kind.addEventListener('change', changeType);
    show();
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();

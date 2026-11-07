document.querySelector('#portal-theme').addEventListener('click', () => {
    const root = document.documentElement;
    root.dataset.bsTheme = root.dataset.bsTheme === 'dark' ? 'light' : 'dark';
    try { localStorage.setItem('portal-theme', root.dataset.bsTheme); } catch {}
});
const search = document.querySelector('#portal-search');
if (search) {
    const input = search.querySelector('input');
    const list = search.querySelector('ul');
    for (const link of document.querySelectorAll('#sidebarMenu a.nav-link')) {
        const item = document.createElement('li');
        const result = document.createElement('a');
        result.href = link.href;
        result.textContent = link.textContent.trim();
        item.append(result);
        list.append(item);
    }
    input.addEventListener('input', () => {
        const query = input.value.trim().toLocaleLowerCase('pt-BR');
        for (const item of list.children) {
            item.hidden = !item.textContent.toLocaleLowerCase('pt-BR').includes(query);
        }
    });
    const open = () => { if (!search.open) search.showModal(); };
    document.querySelector('#portal-search-button').addEventListener('click', open);
    document.addEventListener('keydown', event => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
            event.preventDefault();
            open();
        }
    });
}

/*
 * Kitlig card: the sites and games of your Kitlig instances, each with an Open button.
 * Served and registered by the Kitlig integration; add it from the card picker ("Kitlig").
 *
 * Config: { type: 'custom:kitlig-card', title?, entry_id?, show?: 'both'|'sites'|'games', show_jobs?: boolean }
 */
const REFRESH_MS = 30000;

const esc = (value) =>
  String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

const ago = (iso) => {
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return '';
  const minutes = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  return days === 1 ? 'yesterday' : `${days} days ago`;
};

const STYLE = `
  :host { display: block; }
  ha-card { padding: 16px; }
  .title { font-size: 1.25rem; font-weight: 500; margin: 0 0 12px; }
  .instance + .instance { margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--divider-color); }
  .head { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
  .name { font-weight: 600; }
  .project { color: var(--secondary-text-color); }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--success-color, #43a047); align-self: center; flex: none; }
  .dot.off { background: var(--error-color, #db4437); }
  .jobs { margin-left: auto; font-size: 0.85rem; color: var(--secondary-text-color); white-space: nowrap; }
  .jobs.busy { color: var(--primary-color); font-weight: 500; }
  .bar { height: 3px; border-radius: 2px; background: var(--divider-color); overflow: hidden; margin: -4px 0 12px; }
  .bar > i { display: block; height: 100%; background: var(--primary-color); transition: width 0.4s ease; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 10px; }
  .tile { display: flex; flex-direction: column; gap: 8px; padding: 12px; border-radius: 12px;
    background: var(--secondary-background-color); min-width: 0; }
  .top { display: flex; gap: 10px; align-items: center; min-width: 0; }
  .icon { width: 40px; height: 40px; border-radius: 10px; flex: none; display: grid; place-items: center;
    background: color-mix(in srgb, var(--primary-color) 16%, transparent); color: var(--primary-color); overflow: hidden; }
  .icon.game { background: color-mix(in srgb, var(--accent-color, #ff9800) 18%, transparent); color: var(--accent-color, #ff9800); }
  .icon img { width: 100%; height: 100%; object-fit: cover; }
  .text { min-width: 0; }
  .site { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .meta { font-size: 0.8rem; color: var(--secondary-text-color); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .actions { display: flex; gap: 6px; align-items: center; margin-top: auto; }
  select { flex: 1; min-width: 0; height: 34px; border-radius: 8px; border: 1px solid var(--divider-color);
    background: var(--card-background-color); color: var(--primary-text-color); padding: 0 6px; font: inherit; font-size: 0.85rem; }
  button { height: 34px; padding: 0 14px; border: 0; border-radius: 8px; cursor: pointer; font: inherit; font-weight: 500;
    background: var(--primary-color); color: var(--text-primary-color, #fff); margin-left: auto; }
  button:disabled { opacity: 0.5; cursor: default; }
  button:focus-visible, select:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 2px; }
  .empty, .error { color: var(--secondary-text-color); font-size: 0.9rem; padding: 4px 0; }
  .error { color: var(--error-color, #db4437); }
`;

class KitligCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = {};
    this._instances = null;
    this._error = '';
    this._chosen = {}; // site id -> chosen page file
    this._timer = null;
    this._loading = false;
    this.shadowRoot.addEventListener('click', (event) => this._onClick(event));
    this.shadowRoot.addEventListener('change', (event) => this._onChange(event));
  }

  static getStubConfig() {
    return { show: 'both', show_jobs: true };
  }

  static getConfigForm() {
    return {
      schema: [
        { name: 'title', selector: { text: {} } },
        { name: 'entry_id', selector: { config_entry: { integration: 'kitlig' } } },
        {
          name: 'show',
          selector: {
            select: {
              mode: 'dropdown',
              options: [
                { value: 'both', label: 'Sites and games' },
                { value: 'sites', label: 'Sites only' },
                { value: 'games', label: 'Games only' },
              ],
            },
          },
        },
        { name: 'show_jobs', selector: { boolean: {} } },
      ],
      computeLabel: (field) =>
        ({ title: 'Title', entry_id: 'Instance (all when empty)', show: 'Show', show_jobs: 'Show running jobs' })[field.name],
    };
  }

  setConfig(config) {
    this._config = { show: 'both', show_jobs: true, ...config };
    this._render();
    if (this._hass) this._load();
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._load();
  }

  connectedCallback() {
    this._timer = setInterval(() => this._load(), REFRESH_MS);
    if (this._hass) this._load();
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    this._timer = null;
  }

  getCardSize() {
    return 4;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: 'auto' };
  }

  async _load() {
    if (!this._hass || this._loading) return;
    this._loading = true;
    try {
      const message = { type: 'kitlig/instances' };
      if (this._config.entry_id) message.entry_id = this._config.entry_id;
      const result = await this._hass.callWS(message);
      this._instances = result.instances;
      this._error = '';
    } catch (err) {
      this._error = (err && err.message) || 'Could not load Kitlig.';
    } finally {
      this._loading = false;
    }
    // Do not redraw under an open scene picker.
    if (this.shadowRoot.activeElement && this.shadowRoot.activeElement.tagName === 'SELECT') return;
    this._render();
  }

  _onChange(event) {
    const select = event.target.closest('select[data-site]');
    if (select) this._chosen[select.dataset.site] = select.value;
  }

  async _onClick(event) {
    const button = event.target.closest('button[data-site]');
    if (!button || button.disabled) return;
    const { entry, site } = button.dataset;
    const page = this._chosen[site] || button.dataset.page || undefined;
    // Open the tab during the click itself, so the browser does not treat it as a pop-up.
    const tab = window.open('', '_blank');
    button.disabled = true;
    try {
      const message = { type: 'kitlig/site_url', entry_id: entry, site_id: site };
      if (page) message.page = page;
      const { url } = await this._hass.callWS(message);
      if (tab) {
        tab.opener = null;
        tab.location.href = url;
      } else {
        window.location.assign(url);
      }
    } catch (err) {
      if (tab) tab.close();
      this._error = (err && err.message) || 'Could not open it.';
      this._render();
    } finally {
      button.disabled = false;
    }
  }

  _tile(instance, site) {
    const game = site.kind === 'game';
    const picture = /^(data:image\/|https?:\/\/)/.test(site.icon || '') ? site.icon : '';
    const pages = site.pages || [];
    const chosen = this._chosen[site.site_id];
    const meta = site.description || [game ? 'Game' : 'Site', ago(site.updated)].filter(Boolean).join(' · ');
    const picker =
      pages.length > 1
        ? `<select data-site="${esc(site.site_id)}" aria-label="${game ? 'Scene' : 'Page'}">${pages
            .map((p) => `<option value="${esc(p.file)}"${p.file === chosen ? ' selected' : ''}>${esc(p.name)}</option>`)
            .join('')}</select>`
        : '';
    const first = game && pages.length ? pages[0].file : '';
    return `
      <div class="tile">
        <div class="top">
          <div class="icon ${game ? 'game' : ''}">
            ${picture ? `<img src="${esc(picture)}" alt="">` : `<ha-icon icon="${game ? 'mdi:gamepad-variant' : 'mdi:web'}"></ha-icon>`}
          </div>
          <div class="text">
            <div class="site" title="${esc(site.name)}">${esc(site.name)}</div>
            <div class="meta">${esc(meta)}</div>
          </div>
        </div>
        <div class="actions">
          ${picker}
          <button data-entry="${esc(instance.entry_id)}" data-site="${esc(site.site_id)}" data-page="${esc(first)}">${game ? 'Play' : 'Open'}</button>
        </div>
      </div>`;
  }

  _instance(instance, many) {
    const show = this._config.show;
    const sites = (instance.sites || []).filter(
      (s) => show === 'both' || (show === 'games' ? s.kind === 'game' : s.kind !== 'game'),
    );
    const running = instance.jobs_running || 0;
    const queued = instance.jobs_queued || 0;
    const job = instance.current_job;
    let jobs = '';
    if (this._config.show_jobs) {
      const label = running
        ? `${running} job${running === 1 ? '' : 's'} running${queued ? `, ${queued} queued` : ''}${job && job.label ? ` · ${job.label}` : ''}`
        : queued
          ? `${queued} queued`
          : 'Idle';
      jobs = `<span class="jobs ${running ? 'busy' : ''}">${esc(label)}</span>`;
    }
    const bar =
      this._config.show_jobs && job && job.progress != null
        ? `<div class="bar"><i style="width:${Number(job.progress)}%"></i></div>`
        : '';
    const what = show === 'games' ? 'games' : show === 'sites' ? 'sites' : 'sites or games';
    const body = !instance.connected
      ? '<div class="empty">This Kitlig is not reachable right now.</div>'
      : !instance.project
        ? '<div class="empty">No project is open on this Kitlig.</div>'
        : sites.length
          ? `<div class="grid">${sites.map((s) => this._tile(instance, s)).join('')}</div>`
          : `<div class="empty">No ${what} in this project yet.</div>`;
    const head =
      many || this._config.show_jobs
        ? `<div class="head">
            <span class="dot ${instance.connected ? '' : 'off'}"></span>
            <span class="name">${esc(instance.name)}</span>
            ${instance.project ? `<span class="project">${esc(instance.project)}</span>` : ''}
            ${jobs}
          </div>${bar}`
        : '';
    return `<div class="instance">${head}${body}</div>`;
  }

  _render() {
    const title = this._config.title ? `<h2 class="title">${esc(this._config.title)}</h2>` : '';
    let body;
    if (this._instances === null) {
      body = this._error ? '' : '<div class="empty">Loading…</div>';
    } else if (!this._instances.length) {
      body = '<div class="empty">No Kitlig instance is connected. Add one in Settings, Devices &amp; services.</div>';
    } else {
      const many = this._instances.length > 1;
      body = this._instances.map((i) => this._instance(i, many)).join('');
    }
    const error = this._error ? `<div class="error">${esc(this._error)}</div>` : '';
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card>${title}${body}${error}</ha-card>`;
  }
}

if (!customElements.get('kitlig-card')) {
  customElements.define('kitlig-card', KitligCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: 'kitlig-card',
    name: 'Kitlig',
    description: 'Browse and open the sites and games of your Kitlig instances.',
    preview: false,
    documentationURL: 'https://github.com/UAI-Software-Inc/Kitlig-Home-Assistant-Integration',
  });
}

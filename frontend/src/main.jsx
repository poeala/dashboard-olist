import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap-icons/font/bootstrap-icons.css';
import './styles.css';
import ucasalLogo from './assets/ucasal-logo.png';
import ucasalMark from './assets/ucasal-mark.png';
import { views, selectedView, dashboardUrl, checkDashboard } from './dashboard';

function Icon({ name, ...props }) {
  return <i className={`bi bi-${name}`} aria-hidden="true" {...props} />;
}

function App() {
  const [view, setView] = useState(() => selectedView(window.location.search));
  const [menuOpen, setMenuOpen] = useState(false);
  const [status, setStatus] = useState('checking');
  const [attempt, setAttempt] = useState(0);
  const [frameLoaded, setFrameLoaded] = useState(false);
  const [frameSlow, setFrameSlow] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [fullscreenError, setFullscreenError] = useState('');
  const panel = useRef(null);
  const frame = useRef(null);

  useEffect(() => {
    const onPopState = () => {
      setFrameLoaded(false);
      setFrameSlow(false);
      setView(selectedView(window.location.search));
    };
    const onFullscreen = () => setFullscreen(Boolean(document.fullscreenElement));
    window.addEventListener('popstate', onPopState);
    document.addEventListener('fullscreenchange', onFullscreen);
    return () => {
      window.removeEventListener('popstate', onPopState);
      document.removeEventListener('fullscreenchange', onFullscreen);
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let disposed = false;
    const timer = setTimeout(() => controller.abort(), 15000);
    setStatus('checking');
    setFrameLoaded(false);
    setFrameSlow(false);
    checkDashboard(controller.signal)
      .then(() => { if (!disposed) setStatus('ready'); })
      .catch(() => { if (!disposed) setStatus('offline'); })
      .finally(() => clearTimeout(timer));
    return () => { disposed = true; clearTimeout(timer); controller.abort(); };
  }, [attempt]);

  useEffect(() => {
    if (status !== 'ready' || frameLoaded) return;
    const timer = setTimeout(() => setFrameSlow(true), 20000);
    return () => clearTimeout(timer);
  }, [status, frameLoaded, view.id, attempt]);

  function selectView(next) {
    if (view.id === next.id) return;
    const url = new URL(window.location.href);
    url.searchParams.set('vista', next.id);
    window.history.pushState({}, '', url);
    setFrameLoaded(false);
    setFrameSlow(false);
    setView(next);
  }

  async function toggleFullscreen() {
    setFullscreenError('');
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await panel.current.requestFullscreen();
    } catch {
      setFullscreenError('No se pudo activar la pantalla completa. Podés abrir el dashboard en otra pestaña.');
    }
  }

  function onFrameLoad() {
    // El evento load también ocurre en páginas de error: verificamos el documento.
    try {
      if (!frame.current.contentDocument?.querySelector('#_dash-config')) {
        setStatus('offline');
        return;
      }
      setFrameLoaded(true);
      setFrameSlow(false);
    } catch {
      setStatus('offline');
    }
  }

  return (
    <div className="portal">
      <a className="visually-hidden-focusable skip-link" href="#main-content">Saltar al contenido</a>
      {menuOpen && <button className="sidebar-backdrop" aria-label="Cerrar menú" onClick={() => setMenuOpen(false)} />}
      <aside className={`sidebar ${menuOpen ? 'is-open' : ''}`} aria-label="Navegación principal">
        <a className="brand" href="/" aria-label="UCASAL, inicio"><span className="brand-logo"><img src={ucasalLogo} alt="UCASAL" /></span><span className="brand-tag">Universidad Católica de Salta</span></a>
        <div className="workspace"><span className="workspace-symbol"><Icon name="buildings" /></span><div><strong>Olist Commerce</strong><small>Espacio de análisis</small></div><Icon name="chevron-expand" /></div>
        <div className="nav-caption">ESPACIO DE ANÁLISIS</div>
        <nav className="nav flex-column">
          <a href="#main-content" className="side-link active" aria-current="page" onClick={() => setMenuOpen(false)}><Icon name="grid-1x2" /> Dashboard <span className="active-dot" /></a>
        </nav>
        <div className="nav-caption modules-caption">ÁREAS DEL NEGOCIO</div>
        <div className="nav flex-column">
          <div className="side-link sales-selected"><Icon name="bag" /> Ventas <Icon name="chevron-right" /></div>
          {[['truck', 'Logística'], ['people', 'Clientes'], ['credit-card', 'Pagos']].map(([icon, label]) => (
            <div className="side-link unavailable" key={label}><Icon name={icon} /><span>{label}</span><span className="soon">Pronto</span></div>
          ))}
        </div>
        <div className="sidebar-bottom"><div className="insight-icon"><Icon name="mortarboard" /></div><strong>Análisis de<br />Datos Masivos</strong><p>Maestría en Ciencia de Datos<br />UCASAL</p><div className="sidebar-footer"><span className="small-dot" /> Proyecto académico · Tablero de prueba</div></div>
      </aside>

      <div className="main-shell">
        <header className="topbar">
          <div className="d-flex align-items-center gap-3"><button className="btn menu-toggle" aria-label="Abrir menú" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}><Icon name="list" /></button><span className="breadcrumb-label">UCASAL <Icon name="chevron-right" /> <strong>Dashboard Olist</strong></span></div>
          <div className="d-flex align-items-center gap-3"><span className="topbar-label">UCASAL · ANALÍTICA DE DATOS</span><span className="avatar"><img src={ucasalMark} alt="UCASAL" /></span></div>
        </header>

        <main id="main-content" className="content">
          <div className="page-heading">
            <div className="academic-heading"><div className="eyebrow"><span /> UCASAL · PROYECTO ACADÉMICO</div><h1>Tablero de prueba<span>.</span></h1><p>Presentación del trabajo realizado para la cátedra de <strong>Análisis de Datos Masivos</strong> de la carrera de <strong>Maestría en Ciencia de Datos de UCASAL</strong>.</p><div className="project-authors"><Icon name="people" /><span>Realizado por <strong>Fabio Quaino</strong> y <strong>María Luz Andrade</strong>.</span></div></div>
            <div className={`connection-badge ${status === 'ready' ? 'connected' : ''}`} role="status"><span className="small-dot" />{status === 'ready' ? 'Dashboard conectado' : status === 'checking' ? 'Conectando dashboard' : 'Sin conexión'}</div>
          </div>

          <section className="intro-strip" aria-label="Área de análisis">
            <div className="intro-symbol"><Icon name="graph-up-arrow" /></div><div><span className="section-overline">PANORAMA COMERCIAL</span><h2>Una perspectiva para cada decisión</h2><p>Del resultado general al detalle que hace la diferencia.</p></div><div className="strip-decoration" aria-hidden="true"><span /><span /><span /><span /><span /><span /><span /></div>
          </section>

          <section ref={panel} className="dashboard-panel" aria-label="Dashboard de ventas">
            <div className="panel-heading"><div><span className="panel-title"><Icon name="bag" /> Ventas</span><span className="panel-subtitle"> / {view.name}</span></div><div className="panel-actions"><button className="btn icon-button" title="Volver a cargar el dashboard" aria-label="Volver a cargar el dashboard" onClick={() => setAttempt((value) => value + 1)}><Icon name="arrow-clockwise" /></button><a className="btn icon-button" href={dashboardUrl(view.id, false)} target="_blank" rel="noreferrer" title="Abrir dashboard en otra pestaña" aria-label="Abrir dashboard en otra pestaña"><Icon name="box-arrow-up-right" /></a><button className="btn icon-button" title={fullscreen ? 'Salir de pantalla completa' : 'Pantalla completa'} aria-label={fullscreen ? 'Salir de pantalla completa' : 'Pantalla completa'} onClick={toggleFullscreen}><Icon name={fullscreen ? 'fullscreen-exit' : 'arrows-fullscreen'} /></button></div></div>
            <div className="view-bar"><nav className="nav view-tabs" aria-label="Vistas de ventas">{views.map((item) => <button key={item.id} className={`nav-link ${view.id === item.id ? 'active' : ''}`} aria-current={view.id === item.id ? 'page' : undefined} onClick={() => selectView(item)}><Icon name={item.icon} />{item.name}</button>)}</nav><span className="view-hint">{view.description}</span></div>
            {fullscreenError && <div className="alert alert-warning m-3" role="alert">{fullscreenError}</div>}
            <div className="embed-container" aria-busy={status === 'checking' || (status === 'ready' && !frameLoaded)}>
              {status === 'ready' && <iframe ref={frame} key={`${view.id}-${attempt}`} src={dashboardUrl(view.id)} title={`Dashboard de ventas · ${view.name}`} className={`dashboard-frame ${frameLoaded ? 'loaded' : ''}`} onLoad={onFrameLoad} />}
              {(status !== 'ready' || !frameLoaded) && <div className="embed-message" role="status">
                <div className={`message-icon ${status === 'offline' ? 'offline' : ''}`}><Icon name={status === 'offline' ? 'plug' : 'bar-chart-line'} /></div>
                <span className="section-overline">DASHBOARD DE VENTAS</span>
                <h3>{status === 'offline' ? 'Conectemos con tus datos' : frameSlow ? 'El dashboard está tardando más de lo habitual' : 'Preparando tu espacio de análisis'}</h3>
                <p>{status === 'offline' ? 'No pudimos acceder al dashboard. Verificá que el servicio esté disponible y volvé a intentar.' : 'Estamos cargando los gráficos, indicadores y filtros de tu negocio.'}</p>
                {status === 'offline' || frameSlow ? <button className="btn btn-ucasal" onClick={() => setAttempt((value) => value + 1)}><Icon name="arrow-clockwise" /> Volver a intentar</button> : <span className="spinner-border spinner-border-sm brand-spinner" aria-label="Cargando" />}
                <div className="message-features"><span><Icon name="sliders" /> Filtros interactivos</span><span><Icon name="pie-chart" /> Indicadores de ventas</span><span><Icon name="compass" /> Análisis de negocio</span></div>
              </div>}
            </div>
            <div className="panel-footer"><span><Icon name="info-circle" /> Los filtros se aplican dentro de cada vista.</span><span>OLIST · SALES INTELLIGENCE</span></div>
          </section>
          <footer className="page-footer"><span><strong>UCASAL</strong><span className="footer-divider">/</span> Universidad Católica de Salta</span><span>Fabio Quaino · María Luz Andrade</span></footer>
        </main>
      </div>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>);

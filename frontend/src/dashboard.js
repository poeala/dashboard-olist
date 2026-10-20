export const views = [
  { id: 'gerencial', name: 'Gerencial', icon: 'grid-1x2', description: 'Una mirada integral al desempeño de tu negocio.' },
  { id: 'analitica', name: 'Analítica', icon: 'bar-chart-line', description: 'Explorá las dimensiones y encontrá nuevas perspectivas.' },
  { id: 'decisiones', name: 'Decisiones', icon: 'compass', description: 'Identificá oportunidades para tu próxima decisión.' },
];

export const areas = [
  { id: 'ventas', name: 'Ventas', icon: 'bag', overline: 'PANORAMA COMERCIAL', title: 'Una perspectiva para cada decisión', description: 'Facturación, categorías y evolución del negocio.' },
  { id: 'logistica', name: 'Logística', icon: 'truck', overline: 'DESEMPEÑO LOGÍSTICO', title: 'De la compra a la entrega', description: 'Tiempos, retrasos y fletes para explorar el desempeño de las entregas.' },
  { id: 'clientes', name: 'Clientes', icon: 'people', overline: 'ANÁLISIS DE CLIENTES', title: 'Conocer a quienes compran', description: 'Frecuencia, valor de compra y segmentos del período seleccionado.' },
];

export function selectedArea(search) {
  const requested = new URLSearchParams(search).get('area');
  return areas.find((area) => area.id === requested) || areas[0];
}

export function selectedView(search) {
  const requested = new URLSearchParams(search).get('vista');
  return views.find((view) => view.id === requested) || views[0];
}

export function dashboardUrl(view, embedded = true, area = 'ventas') {
  const valid = views.some((item) => item.id === view) ? view : 'gerencial';
  const validArea = areas.some((item) => item.id === area) ? area : 'ventas';
  return `/dashboard/?${new URLSearchParams({ area: validArea, vista: valid, ...(embedded ? { embed: '1' } : {}) })}`;
}

export async function checkDashboard(signal) {
  const response = await fetch('/dashboard/healthz', { signal, cache: 'no-store' });
  if (!response.ok) throw new Error('Dashboard no disponible');
  const data = await response.json();
  if (data.status !== 'ok' || data.service !== 'olist-dashboard') {
    throw new Error('Respuesta inesperada del dashboard');
  }
}

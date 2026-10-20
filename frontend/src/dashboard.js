export const views = [
  { id: 'gerencial', name: 'Gerencial', icon: 'grid-1x2', description: 'Una mirada integral al desempeño de tu negocio.' },
  { id: 'analitica', name: 'Analítica', icon: 'bar-chart-line', description: 'Explorá las dimensiones y encontrá nuevas perspectivas.' },
  { id: 'decisiones', name: 'Decisiones', icon: 'compass', description: 'Identificá oportunidades para tu próxima decisión.' },
];

export function selectedView(search) {
  const requested = new URLSearchParams(search).get('vista');
  return views.find((view) => view.id === requested) || views[0];
}

export function dashboardUrl(view, embedded = true) {
  const valid = views.some((item) => item.id === view) ? view : 'gerencial';
  return `/dashboard/?${new URLSearchParams({ vista: valid, ...(embedded ? { embed: '1' } : {}) })}`;
}

export async function checkDashboard(signal) {
  const response = await fetch('/dashboard/healthz', { signal, cache: 'no-store' });
  if (!response.ok) throw new Error('Dashboard no disponible');
  const data = await response.json();
  if (data.status !== 'ok' || data.service !== 'olist-dashboard') {
    throw new Error('Respuesta inesperada del dashboard');
  }
}

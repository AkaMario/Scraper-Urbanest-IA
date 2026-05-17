import { useEffect, useState } from "react";

const COP = new Intl.NumberFormat("es-CO", {
  style: "currency",
  currency: "COP",
  maximumFractionDigits: 0,
});

function AdminPanel({ apiUrl, onBack }) {
  const [properties, setProperties] = useState([]);
  const [stats, setStats] = useState([]);
  const [filters, setFilters] = useState({ city: "", status: "active", operation: "" });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.set(key, value);
    });
    params.set("limit", "200");
    setLoading(true);
    Promise.all([
      fetch(`${apiUrl}/api/properties?${params.toString()}`, { signal: controller.signal }).then((res) => res.json()),
      fetch(`${apiUrl}/api/properties/stats`, { signal: controller.signal }).then((res) => res.json()),
    ])
      .then(([nextProperties, nextStats]) => {
        setProperties(Array.isArray(nextProperties) ? nextProperties : []);
        setStats(Array.isArray(nextStats) ? nextStats : []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [apiUrl, filters]);

  const updateFilter = (event) => {
    setFilters((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  return (
    <div className="min-h-screen bg-[#111827] px-4 py-5 text-slate-100 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <div className="flex flex-col gap-4 border-b border-white/10 pb-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-cyan-300">Admin</p>
            <h1 className="mt-2 text-2xl font-semibold text-white">Inventario de inmuebles</h1>
            <p className="mt-1 text-sm text-slate-400">Propiedades guardadas en Postgres para Cartagena y Barranquilla.</p>
          </div>
          <button className="rounded-xl border border-white/10 px-4 py-2 text-sm text-slate-200 hover:bg-white/10" onClick={onBack} type="button">
            Volver al chat
          </button>
        </div>

        <div className="grid gap-3 py-5 sm:grid-cols-3 lg:grid-cols-6">
          {stats.map((item) => (
            <div key={`${item.city}-${item.operation}-${item.status}`} className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs text-slate-400">{item.city || "Sin ciudad"}</p>
              <p className="mt-1 text-xl font-semibold text-white">{item.count}</p>
              <p className="mt-1 text-xs text-slate-500">{item.operation} · {item.status}</p>
            </div>
          ))}
        </div>

        <div className="mb-5 grid gap-3 rounded-2xl border border-white/10 bg-white/[0.03] p-4 sm:grid-cols-3">
          <select className="rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm" name="city" value={filters.city} onChange={updateFilter}>
            <option value="">Todas las ciudades</option>
            <option value="Cartagena">Cartagena</option>
            <option value="Barranquilla">Barranquilla</option>
          </select>
          <select className="rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm" name="operation" value={filters.operation} onChange={updateFilter}>
            <option value="">Venta y arriendo</option>
            <option value="rent">Arriendo</option>
            <option value="sale">Venta</option>
          </select>
          <select className="rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-sm" name="status" value={filters.status} onChange={updateFilter}>
            <option value="active">Activas</option>
            <option value="inactive">Inactivas</option>
            <option value="">Todas</option>
          </select>
        </div>

        <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.03]">
          <div className="border-b border-white/10 px-4 py-3 text-sm text-slate-400">
            {loading ? "Cargando inventario..." : `${properties.length} propiedades`}
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-white/10 text-left text-sm">
              <thead className="bg-black/20 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Propiedad</th>
                  <th className="px-4 py-3">Ciudad</th>
                  <th className="px-4 py-3">Operación</th>
                  <th className="px-4 py-3">Precio</th>
                  <th className="px-4 py-3">Fuente</th>
                  <th className="px-4 py-3">Estado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {properties.map((property) => (
                  <tr key={property.id} className="hover:bg-white/[0.03]">
                    <td className="max-w-md px-4 py-3">
                      <a className="font-medium text-cyan-200 hover:text-cyan-100" href={property.url} target="_blank" rel="noreferrer">
                        {property.title}
                      </a>
                      <p className="mt-1 truncate text-xs text-slate-500">{property.neighborhood || property.zone || "Sin barrio"}</p>
                    </td>
                    <td className="px-4 py-3 text-slate-300">{property.city}</td>
                    <td className="px-4 py-3 text-slate-300">{property.operation === "sale" ? "Venta" : "Arriendo"}</td>
                    <td className="px-4 py-3 text-slate-300">{property.price ? COP.format(property.price) : "-"}</td>
                    <td className="px-4 py-3 text-slate-300">{property.source}</td>
                    <td className="px-4 py-3 text-slate-300">{property.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AdminPanel;

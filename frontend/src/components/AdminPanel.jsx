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
  const [searchTerm, setSearchTerm] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
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
  }, [apiUrl, filters, refreshKey]);

  const updateFilter = (event) => {
    setFilters((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const normalizedSearch = searchTerm.trim().toLowerCase();
  const visibleProperties = normalizedSearch
    ? properties.filter((property) => {
        const haystack = [
          property.title,
          property.description,
          property.city,
          property.zone,
          property.neighborhood,
          property.property_type,
          property.source,
          property.status,
          property.operation === "sale" ? "venta" : "arriendo",
          property.price,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(normalizedSearch);
      })
    : properties;

  return (
    <div className="min-h-screen bg-black px-4 py-4 text-zinc-100 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <div className="flex flex-col gap-4 pb-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-medium text-zinc-500">Urbanest IA</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-white sm:text-3xl">Inventario</h1>
            <p className="mt-2 text-sm text-zinc-500">Propiedades guardadas en Postgres para Cartagena y Barranquilla.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              className="rounded-full border border-white/10 bg-[#111] px-4 py-2 text-sm text-zinc-300 transition hover:bg-white/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
              onClick={() => setRefreshKey((current) => current + 1)}
              type="button"
              disabled={loading}
            >
              {loading ? "Actualizando" : "Refrescar tabla"}
            </button>
            <button className="rounded-full border border-white/10 bg-[#111] px-4 py-2 text-sm text-zinc-300 transition hover:bg-white/10 hover:text-white" onClick={onBack} type="button">
              Volver al chat
            </button>
          </div>
        </div>

        <div className="grid gap-3 pb-5 sm:grid-cols-3 lg:grid-cols-6">
          {stats.map((item) => (
            <div key={`${item.city}-${item.operation}-${item.status}`} className="rounded-3xl border border-white/10 bg-[#111] p-4">
              <p className="truncate text-xs text-zinc-500">{item.city || "Sin ciudad"}</p>
              <p className="mt-2 text-2xl font-semibold text-white">{item.count}</p>
              <p className="mt-1 text-xs text-zinc-600">{item.operation === "sale" ? "venta" : "arriendo"} · {item.status}</p>
            </div>
          ))}
        </div>

        <div className="mb-5 grid gap-3 rounded-[28px] border border-white/10 bg-[#111] p-3 shadow-[0_18px_60px_rgba(0,0,0,0.35)] lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
          <div className="relative">
            <input
              className="w-full rounded-full border border-white/10 bg-black px-4 py-3 text-sm text-white outline-none placeholder:text-zinc-500 transition focus:border-white/25"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Buscar por barrio, título, fuente, precio..."
            />
          </div>
          <select className="rounded-full border border-white/10 bg-black px-4 py-3 text-sm text-zinc-200 outline-none transition focus:border-white/25" name="city" value={filters.city} onChange={updateFilter}>
            <option value="">Todas las ciudades</option>
            <option value="Cartagena">Cartagena</option>
            <option value="Barranquilla">Barranquilla</option>
          </select>
          <select className="rounded-full border border-white/10 bg-black px-4 py-3 text-sm text-zinc-200 outline-none transition focus:border-white/25" name="operation" value={filters.operation} onChange={updateFilter}>
            <option value="">Venta y arriendo</option>
            <option value="rent">Arriendo</option>
            <option value="sale">Venta</option>
          </select>
          <select className="rounded-full border border-white/10 bg-black px-4 py-3 text-sm text-zinc-200 outline-none transition focus:border-white/25" name="status" value={filters.status} onChange={updateFilter}>
            <option value="active">Activas</option>
            <option value="inactive">Inactivas</option>
            <option value="">Todas</option>
          </select>
        </div>

        <div className="overflow-hidden rounded-[28px] border border-white/10 bg-[#111]">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-4 text-sm text-zinc-500">
            {loading ? "Cargando inventario..." : `${visibleProperties.length} de ${properties.length} propiedades`}
            <span className="rounded-full border border-white/10 bg-black px-3 py-1 text-xs text-zinc-500">DB local</span>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-white/10 text-left text-sm">
              <thead className="bg-black text-xs uppercase tracking-wide text-zinc-600">
                <tr>
                  <th className="px-4 py-3">Propiedad</th>
                  <th className="px-4 py-3">Ciudad</th>
                  <th className="px-4 py-3">Operación</th>
                  <th className="px-4 py-3">Precio</th>
                  <th className="px-4 py-3">Fuente</th>
                  <th className="px-4 py-3">Estado</th>
                  <th className="px-4 py-3">Ausencias</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {visibleProperties.map((property) => (
                  <tr key={property.id} className="transition hover:bg-white/[0.04]">
                    <td className="max-w-md px-4 py-3">
                      <a className="font-medium text-zinc-100 hover:text-white" href={property.url} target="_blank" rel="noreferrer">
                        {property.title}
                      </a>
                      <p className="mt-1 truncate text-xs text-zinc-500">{property.neighborhood || property.zone || "Sin barrio"}</p>
                    </td>
                    <td className="px-4 py-3 text-zinc-300">{property.city}</td>
                    <td className="px-4 py-3 text-zinc-300">{property.operation === "sale" ? "Venta" : "Arriendo"}</td>
                    <td className="px-4 py-3 font-medium text-zinc-100">{property.price ? COP.format(property.price) : "-"}</td>
                    <td className="px-4 py-3 text-zinc-300">{property.source}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2.5 py-1 text-xs ${property.status === "active" ? "bg-white text-black" : "bg-zinc-800 text-zinc-400"}`}>
                        {property.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-zinc-300">{property.missing_count || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {visibleProperties.length === 0 ? (
              <div className="px-4 py-12 text-center text-sm text-zinc-500">
                No hay inmuebles que coincidan con los filtros actuales.
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AdminPanel;

function formatCurrency(value) {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function ResultCard({ property, compact = false, horizontal = false }) {
  const hasImage = Boolean(property.image_url);
  const visibleFeatures = Array.isArray(property.features)
    ? property.features.slice(0, horizontal ? 3 : compact ? 4 : 8)
    : [];
  const location = property.neighborhood || property.zone || "Cartagena";
  const imageClass = horizontal
    ? "h-36 sm:h-40"
    : compact
      ? "h-32 sm:h-36 md:h-full"
      : "h-40 sm:h-48";
  const cardClass = horizontal
    ? "snap-start overflow-hidden rounded-[22px] border border-white/10 bg-[#171923] shadow-lg shadow-black/10"
    : "overflow-hidden rounded-[22px] border border-white/10 bg-[#171923]/80 shadow-lg shadow-black/10";
  const contentGridClass = horizontal
    ? "grid gap-3 p-3"
    : `grid gap-3 p-3 sm:gap-4 sm:p-4 ${compact ? "md:grid-cols-[132px_1fr]" : ""}`;

  return (
    <article className={cardClass}>
      <div className={contentGridClass}>
        {hasImage ? (
          <div className="relative overflow-hidden rounded-[1rem] border border-white/10 bg-white/[0.03]">
            <img
              src={property.image_url}
              alt={property.title}
              className={`${imageClass} w-full object-cover transition duration-300 hover:scale-[1.03]`}
            />
            <span className="absolute left-2 top-2 rounded-full bg-black/60 px-2.5 py-1 text-[11px] font-medium text-white backdrop-blur">
              {property.source}
            </span>
          </div>
        ) : (
          <div
            className={`${imageClass} flex w-full items-center justify-center rounded-[1rem] border border-dashed border-white/10 bg-white/[0.03] px-4 text-center text-xs leading-5 text-slate-500`}
          >
            Sin imagen disponible
          </div>
        )}
        <div className="min-w-0">
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between">
            <div className="min-w-0">
              <h3 className="line-clamp-2 text-sm font-semibold leading-6 text-white sm:text-base">{property.title}</h3>
              <p className="mt-1 line-clamp-1 text-xs text-slate-400 sm:text-sm">
                {location} · {property.property_type || "Inmueble"}
              </p>
            </div>
            <p className="w-fit rounded-full bg-emerald-500/15 px-3 py-1 text-sm font-semibold text-emerald-200 ring-1 ring-emerald-400/15">
              {formatCurrency(property.price)}
            </p>
          </div>

          <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-300">
            {property.description || "Sin descripcion disponible en la fuente."}
          </p>

          <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-300">
            <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
              {property.bedrooms ?? "N/D"} hab
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
              {property.bathrooms ?? "N/D"} baños
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
              {property.area_m2 ?? "N/D"} m²
            </span>
          </div>

          {visibleFeatures.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-300">
              {visibleFeatures.map((feature) => (
                <span key={feature} className="line-clamp-1 rounded-full border border-emerald-400/15 bg-emerald-400/5 px-2.5 py-1 text-emerald-100">
                  {feature}
                </span>
              ))}
            </div>
          ) : null}

          <a
            className="mt-4 inline-flex w-full justify-center rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-sm font-medium text-white transition hover:border-emerald-400/30 hover:bg-emerald-400/10 sm:w-auto"
            href={property.url}
            target="_blank"
            rel="noreferrer"
          >
            Ver anuncio
          </a>
        </div>
      </div>
    </article>
  );
}

export default ResultCard;

function formatCurrency(value) {
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(value || 0);
}

function ResultCard({ property, compact = false }) {
  const hasImage = Boolean(property.image_url);

  return (
    <article className="overflow-hidden rounded-2xl border border-white/8 bg-black/10">
      <div className={`grid gap-3 p-3 sm:gap-4 sm:p-4 ${compact ? "md:grid-cols-[96px_1fr]" : ""}`}>
        {hasImage ? (
          <img
            src={property.image_url}
            alt={property.title}
            className={`${compact ? "h-24 md:h-full" : "h-36"} w-full rounded-[1rem] object-cover`}
          />
        ) : (
          <div
            className={`${compact ? "h-24 md:h-full" : "h-36"} flex w-full items-center justify-center rounded-[1rem] border border-dashed border-white/10 bg-white/[0.03] px-4 text-center text-xs leading-5 text-slate-500`}
          >
            Sin imagen disponible
          </div>
        )}
        <div>
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between">
            <div className="min-w-0">
              <h3 className="text-sm font-semibold leading-6 text-white sm:text-base">{property.title}</h3>
              <p className="mt-1 text-sm text-slate-400">
                {property.neighborhood || property.zone || "Cartagena"} · {property.source}
              </p>
            </div>
            <p className="w-fit rounded-full bg-emerald-500/15 px-3 py-1 text-sm font-semibold text-emerald-300">
              {formatCurrency(property.price)}
            </p>
          </div>

          <p className="mt-3 text-sm leading-6 text-slate-300">{property.description}</p>

          <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-300">
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
              {property.bedrooms ?? "N/D"} hab
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
              {property.bathrooms ?? "N/D"} baños
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">
              {property.area_m2 ?? "N/D"} m²
            </span>
          </div>

          <a
            className="mt-4 inline-flex w-full justify-center rounded-full border border-white/10 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/10 sm:w-auto"
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

import { getStatus } from "@/lib/api";

export default async function OperationalStatus() {
  let status: Awaited<ReturnType<typeof getStatus>> | null = null;

  try {
    status = await getStatus();
  } catch {
    return (
      <p className="mt-2 text-xs text-stone-400">
        Estado no disponible
      </p>
    );
  }

  const apiOk = status.api === "ok";
  const workers = status.workers;
  const lastFinished = Object.values(workers)
    .map((w) => (w as { finished_at?: string | null }).finished_at)
    .filter((v): v is string => typeof v === "string" && v.length > 0)
    .sort()
    .reverse()[0];

  const lastDate = lastFinished
    ? new Date(lastFinished).toLocaleDateString("es-ES", { year: "numeric", month: "short", day: "numeric" })
    : null;

  return (
    <p className="mt-2 flex items-center gap-1.5 text-xs text-stone-400">
      <span className={`inline-block h-1.5 w-1.5 rounded-full ${apiOk ? "bg-green-600" : "bg-amber-600"}`} />
      {apiOk ? "Sistema operativo" : "Estado degradado"}
      {lastDate && <span>\u00b7 Actualizado {lastDate}</span>}
    </p>
  );
}

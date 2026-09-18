import StatusBadge from "./StatusBadge";

interface MetricCardProps {
  title: string;
  status: string;
  description?: string;
}

export default function MetricCard({ title, status, description }: MetricCardProps) {
  return (
    <div className="bg-white border border-moss-100 rounded-lg p-4 flex flex-col gap-2 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-ink/80">{title}</h3>
        <StatusBadge status={status} />
      </div>
      {description && <p className="text-xs text-ink/50 leading-snug">{description}</p>}
    </div>
  );
}

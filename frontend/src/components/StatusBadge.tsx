interface StatusBadgeProps {
  status: string;
}

const STATUS_STYLES: Record<string, string> = {
  Low: "bg-alert/10 text-alert border-alert/30",
  Moderate: "bg-soil-500/10 text-soil-500 border-soil-500/30",
  High: "bg-moss-100 text-moss-700 border-moss-300",
  Unknown: "bg-gray-100 text-gray-500 border-gray-200",
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.Unknown;
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${style}`}>
      {status}
    </span>
  );
}

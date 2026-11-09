export default function MoodBadge({ mood, className = "" }) {
  if (!mood) return null;

  const configs = {
    positive: { color: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30", text: "Positive" },
    neutral: { color: "bg-gray-500/20 text-gray-400 border border-gray-500/30", text: "Neutral" },
    negative: { color: "bg-rose-500/20 text-rose-400 border border-rose-500/30", text: "Negative" },
    urgent: { color: "bg-amber-500/20 text-amber-400 border border-amber-500/30 font-semibold", text: "Urgent" },
  };

  const config = configs[mood] || { color: "bg-gray-700 text-gray-300 border border-dark-600", text: mood };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium tracking-wide ${config.color} ${className}`}>
      {config.text}
    </span>
  );
}

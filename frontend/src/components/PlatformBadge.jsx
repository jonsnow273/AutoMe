export default function PlatformBadge({ platform, className = "" }) {
  const configs = {
    discord: { color: "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30", text: "Discord" },
    whatsapp: { color: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30", text: "WhatsApp" },
    instagram: { color: "bg-pink-500/20 text-pink-400 border border-pink-500/30", text: "Instagram" },
  };

  const config = configs[platform] || { color: "bg-gray-700 text-gray-300 border border-dark-600", text: platform };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wide ${config.color} ${className}`}>
      {config.text}
    </span>
  );
}

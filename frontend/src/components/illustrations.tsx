/** Original inline SVG assets: badge icons (learning/skill/collaboration), membership art.
 *  All original, offline-capable, no external images (UX-06). */

export function BadgeIcon({ svgId, className }: { svgId: string; className?: string }) {
  const common = { fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  if (svgId === "badge-skill")
    return (
      <svg viewBox="0 0 64 64" className={className} aria-hidden>
        <circle cx="32" cy="26" r="16" {...common} />
        <path d="M24 40l-5 18 13-6 13 6-5-18" {...common} />
        <path d="M25 26l5 5 9-10" {...common} />
      </svg>
    );
  if (svgId === "badge-collab")
    return (
      <svg viewBox="0 0 64 64" className={className} aria-hidden>
        <circle cx="32" cy="26" r="16" {...common} />
        <path d="M24 40l-5 18 13-6 13 6-5-18" {...common} />
        <circle cx="26" cy="24" r="3" {...common} /><circle cx="38" cy="24" r="3" {...common} />
        <path d="M26 31c2 3 10 3 12 0" {...common} />
      </svg>
    );
  // default: badge-learning
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden>
      <circle cx="32" cy="26" r="16" {...common} />
      <path d="M24 40l-5 18 13-6 13 6-5-18" {...common} />
      <path d="M24 22h16M24 27h16M24 32h10" {...common} />
    </svg>
  );
}

export function TierArt({ level, className }: { level: number; className?: string }) {
  return (
    <svg viewBox="0 0 80 44" className={className} aria-hidden>
      <path d="M6 38 L26 22 L46 30 L74 8" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="4 3" strokeLinecap="round" />
      {Array.from({ length: 3 }).map((_, i) => (
        <circle key={i} cx={10 + i * 28} cy={[36, 24, 12][i]} r="5"
          fill={level >= i + 1 ? "currentColor" : "none"} stroke="currentColor" strokeWidth="1.6" />
      ))}
    </svg>
  );
}

export function MembershipArt({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 120 60" className={className} aria-hidden>
      <g fill="none" stroke="currentColor" strokeWidth="1.6">
        <rect x="6" y="10" width="108" height="40" rx="8" />
        <path d="M14 22h30M14 30h20" strokeLinecap="round" />
        <circle cx="92" cy="30" r="12" strokeDasharray="3 3" />
      </g>
    </svg>
  );
}

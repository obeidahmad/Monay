import { useId } from "react";
import styles from "./Logo.module.css";

/**
 * The Monay mark: an M drawn as one ribbon that rises — two peaks, the second
 * higher than the first, the way a pot grows from month to month — with a coin
 * dropping into the valley. On a mint-to-teal tile.
 */
export function Mark({ size = 36, className }: { size?: number; className?: string }) {
  const id = useId();
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 48 48"
      width={size}
      height={size}
      role="img"
      aria-label="Monay"
      className={className}
    >
      <defs>
        <linearGradient id={`${id}-tile`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#5cf0b0" />
          <stop offset="0.55" stopColor="#3ddc97" />
          <stop offset="1" stopColor="#12a8b8" />
        </linearGradient>
        <linearGradient id={`${id}-shine`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity="0.45" />
          <stop offset="0.5" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
      </defs>
      <rect width="48" height="48" rx="15" fill={`url(#${id}-tile)`} />
      <rect width="48" height="48" rx="15" fill={`url(#${id}-shine)`} />
      {/* the ribbon M: left peak lower, right peak higher */}
      <path
        d="M11 35V21.5a3.4 3.4 0 0 1 6-2.2l7 8.4 7-11.2a3.4 3.4 0 0 1 6.3 1.8V35"
        fill="none"
        stroke="#0e0e12"
        strokeWidth="4.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* the coin */}
      <circle cx="24" cy="13.2" r="3.4" fill="#0e0e12" />
    </svg>
  );
}

/** The mark with the name beside it. */
export function Logo({ size = 36, className }: { size?: number; className?: string }) {
  return (
    <span className={`${styles.logo} ${className ?? ""}`}>
      <Mark size={size} />
      <span className={styles.name} style={{ fontSize: size * 0.62 }}>
        Monay
      </span>
    </span>
  );
}

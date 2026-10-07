/**
 * The Monay logo: the name in Manrope ExtraBold, outlined so no font has to be
 * loaded for it. Path data is copied from the design system's Logo assets — do
 * not redraw, stretch or restyle it.
 */

const M = "M140 0V1440H384L860 484L1336 1440H1580V0H1326V860L908 0H812L394 860V0Z";

const LETTERS: { x: number; d: string }[] = [
  { x: 0, d: M },
  {
    x: 170.8,
    d: "M626 -30Q463 -30 340.0 43.0Q217 116 148.5 244.5Q80 373 80 540Q80 709 150.0 837.5Q220 966 343.0 1038.0Q466 1110 626 1110Q789 1110 912.5 1037.0Q1036 964 1105.0 835.5Q1174 707 1174 540Q1174 372 1104.5 243.5Q1035 115 911.5 42.5Q788 -30 626 -30ZM626 224Q757 224 821.5 312.5Q886 401 886 540Q886 684 820.5 770.0Q755 856 626 856Q537 856 480.0 816.0Q423 776 395.5 705.0Q368 634 368 540Q368 395 433.5 309.5Q499 224 626 224Z",
  },
  {
    x: 295,
    d: "M876 0V510Q876 547 872.0 604.5Q868 662 847.0 720.0Q826 778 778.5 817.0Q731 856 644 856Q609 856 569.0 845.0Q529 834 494.0 802.5Q459 771 436.5 710.0Q414 649 414 548V0H138V1080H380V969Q417 1011 467 1043Q571 1112 730 1112Q857 1112 937.0 1069.0Q1017 1026 1061.5 960.0Q1106 894 1125.0 822.5Q1144 751 1148.0 692.0Q1152 633 1152 606V0Z",
  },
  {
    x: 421,
    d: "M440 -30Q324 -30 243.5 14.5Q163 59 121.5 133.5Q80 208 80 298Q80 373 103.0 435.0Q126 497 177.5 544.5Q229 592 316 624Q376 646 459.0 663.0Q542 680 647 696Q709 705 778 715Q770 782 734 817Q688 862 580 862Q520 862 455.0 833.0Q390 804 364 730L118 808Q159 942 272.0 1026.0Q385 1110 580 1110Q723 1110 834.0 1066.0Q945 1022 1002 914Q1034 854 1040.0 794.0Q1046 734 1046 660V0H808V133Q744 57 672 19Q580 -30 440 -30ZM498 184Q573 184 624.5 210.5Q676 237 706.5 271.0Q737 305 748 328Q769 372 773 431Q775 466 775 495Q708 483 660 475Q585 461 539.0 450.0Q493 439 458 426Q418 410 393.5 391.5Q369 373 357.5 351.0Q346 329 346 302Q346 265 364.5 238.5Q383 212 417.0 198.0Q451 184 498 184Z",
  },
  { x: 536.4, d: "M278 -480 456 9 20 1080H302L586 345L868 1080H1140L530 -480Z" },
];

interface WordmarkProps {
  /** Rendered height in px (minimum 20). */
  height?: number;
  className?: string;
}

/**
 * The wordmark. It takes the current text colour, so it is white in dark mode
 * and ink in white mode when placed in `text-strong`.
 */
export function Wordmark({ height = 28, className }: WordmarkProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="-2 -146 654.4 196"
      height={height}
      role="img"
      aria-label="Monay"
      className={className}
      fill="currentColor"
    >
      {LETTERS.map((letter) => (
        <path key={letter.x} transform={`translate(${letter.x} 0) scale(0.1 -0.1)`} d={letter.d} />
      ))}
    </svg>
  );
}

/** The app icon: a mint M on an ink tile (brand colours, the same in both themes). */
export function Monogram({ size = 40, className }: { size?: number; className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 100 100"
      width={size}
      height={size}
      role="img"
      aria-label="Monay"
      className={className}
    >
      <rect width="100" height="100" rx="30" fill="var(--brand-ink)" />
      <path transform="translate(5.28 87.44) scale(0.05 -0.05)" d={M} fill="var(--brand-mint)" />
    </svg>
  );
}

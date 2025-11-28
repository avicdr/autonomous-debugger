import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export const BackgroundDoodles = () => {
  const { theme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  const isDark = theme === "dark";

  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden">
      <svg
        className="absolute inset-0 w-full h-full"
        style={{ opacity: isDark ? 0.25 : 0.2 }}
      >
        <defs>
          <pattern
            id="doodles"
            x="0"
            y="0"
            width="200"
            height="200"
            patternUnits="userSpaceOnUse"
          >
            {/* Curly brackets */}
            <text
              x="20"
              y="40"
              fontSize="24"
              fill={isDark ? "#00ffc8" : "#6366f1"}
              fontFamily="monospace"
            >
              {"{"}
            </text>
            <text
              x="150"
              y="80"
              fontSize="24"
              fill={isDark ? "#00ffc8" : "#6366f1"}
              fontFamily="monospace"
            >
              {"}"}
            </text>

            {/* Python snake */}
            <path
              d="M 60 120 Q 70 110 80 120 T 100 120"
              stroke={isDark ? "#a855f7" : "#8b5cf6"}
              strokeWidth="2"
              fill="none"
            />
            <circle cx="58" cy="118" r="2" fill={isDark ? "#a855f7" : "#8b5cf6"} />

            {/* Gear */}
            <circle
              cx="140"
              cy="150"
              r="8"
              stroke={isDark ? "#06b6d4" : "#14b8a6"}
              strokeWidth="2"
              fill="none"
            />
            <circle cx="140" cy="150" r="4" fill={isDark ? "#06b6d4" : "#14b8a6"} />

            {/* Sparkles */}
            <path
              d="M 30 170 L 32 175 L 37 177 L 32 179 L 30 184 L 28 179 L 23 177 L 28 175 Z"
              fill={isDark ? "#84cc16" : "#f59e0b"}
            />

            {/* Arrows */}
            <path
              d="M 170 30 L 180 35 L 170 40"
              stroke={isDark ? "#00d9ff" : "#06b6d4"}
              strokeWidth="2"
              fill="none"
            />
            <path
              d="M 100 170 L 90 165 L 100 160"
              stroke={isDark ? "#00d9ff" : "#06b6d4"}
              strokeWidth="2"
              fill="none"
            />

            {/* Code symbol */}
            <text
              x="120"
              y="120"
              fontSize="18"
              fill={isDark ? "#818cf8" : "#a78bfa"}
              fontFamily="monospace"
            >
              &lt;/&gt;
            </text>
          </pattern>
        </defs>

        <rect width="100%" height="100%" fill="url(#doodles)" />
      </svg>

      {/* Floating particles for dark mode */}
      {isDark && (
        <div className="absolute inset-0">
          {[...Array(15)].map((_, i) => (
            <div
              key={i}
              className="absolute w-1.5 h-1.5 bg-primary-glow rounded-full animate-pulse-glow"
              style={{
                left: `${Math.random() * 100}%`,
                top: `${Math.random() * 100}%`,
                opacity: 0.3,
                animationDelay: `${Math.random() * 3}s`,
                animationDuration: `${3 + Math.random() * 2}s`,
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
};

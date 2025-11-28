interface AnimatedDoodleProps {
  type: "snake" | "robot" | "gear";
  className?: string;
}

export const AnimatedDoodle = ({ type, className = "" }: AnimatedDoodleProps) => {
  if (type === "snake") {
    return (
      <div className={`relative ${className}`}>
        <svg width="80" height="80" viewBox="0 0 80 80" className="animate-pulse-glow">
          <path
            d="M 20 40 Q 30 20 40 40 T 60 40"
            stroke="currentColor"
            strokeWidth="4"
            fill="none"
            strokeLinecap="round"
            className="text-primary-glow"
          />
          <circle cx="18" cy="38" r="3" fill="currentColor" className="text-primary" />
          <circle cx="16" cy="36" r="1.5" fill="currentColor" className="text-primary-foreground" />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xs text-primary-glow animate-pulse">🐍</span>
        </div>
      </div>
    );
  }

  if (type === "robot") {
    return (
      <div className={`relative ${className}`}>
        <svg width="80" height="80" viewBox="0 0 80 80">
          <rect
            x="25"
            y="30"
            width="30"
            height="30"
            rx="4"
            stroke="currentColor"
            strokeWidth="2"
            fill="none"
            className="text-accent animate-pulse-glow"
          />
          <circle cx="35" cy="42" r="2" fill="currentColor" className="text-accent" />
          <circle cx="45" cy="42" r="2" fill="currentColor" className="text-accent" />
          <rect
            x="32"
            y="50"
            width="16"
            height="2"
            rx="1"
            fill="currentColor"
            className="text-accent"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl animate-pulse">🤖</span>
        </div>
      </div>
    );
  }

  if (type === "gear") {
    return (
      <div className={`relative ${className}`}>
        <svg
          width="80"
          height="80"
          viewBox="0 0 80 80"
          className="animate-spin"
          style={{ animationDuration: "8s" }}
        >
          <circle
            cx="40"
            cy="40"
            r="15"
            stroke="currentColor"
            strokeWidth="3"
            fill="none"
            className="text-secondary"
          />
          <circle cx="40" cy="40" r="8" fill="currentColor" className="text-secondary" />
          {[0, 60, 120, 180, 240, 300].map((angle) => (
            <rect
              key={angle}
              x="38"
              y="20"
              width="4"
              height="10"
              fill="currentColor"
              className="text-secondary"
              transform={`rotate(${angle} 40 40)`}
            />
          ))}
        </svg>
      </div>
    );
  }

  return null;
};

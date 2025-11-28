import { CheckCircle2, XCircle, Clock, Copy, RotateCw, Trash2, Terminal as TerminalIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AnimatedDoodle } from "./AnimatedDoodle";
import { useToast } from "@/hooks/use-toast";

interface LogLine {
  type: "success" | "error" | "warning" | "info" | "ai";
  content: string;
}

interface EnhancedOutputTerminalProps {
  output: string;
  status: "idle" | "success" | "error";
  responseTime?: number;
  isLoading?: boolean;
  onClear?: () => void;
  onRefresh?: () => void;
}

const loadingMessages = [
  { text: "🔍 Sniffing out bugs...", icon: "snake" },
  { text: "🧠 Thinking harder than my training compute...", icon: "robot" },
  { text: "😼 Stealing your code (jk)", icon: "gear" },
  { text: "🪄 Casting spells on your code...", icon: "robot" },
  { text: "🐍 Making peace with Python exceptions...", icon: "snake" },
  { text: "🎯 Debugging like a boss...", icon: "gear" },
] as const;

export const EnhancedOutputTerminal = ({
  output,
  status,
  responseTime,
  isLoading,
  onClear,
  onRefresh,
}: EnhancedOutputTerminalProps) => {
  const { toast } = useToast();
  const randomMsg = loadingMessages[Math.floor(Math.random() * loadingMessages.length)];

  const parseLogLines = (text: string): LogLine[] => {
    const lines = text.split("\n");
    return lines.map((line) => {
      if (line.toLowerCase().includes("error") || line.toLowerCase().includes("traceback")) {
        return { type: "error", content: line };
      }
      if (line.toLowerCase().includes("warning")) {
        return { type: "warning", content: line };
      }
      if (line.toLowerCase().includes("success") || line.toLowerCase().includes("completed")) {
        return { type: "success", content: line };
      }
      if (line.toLowerCase().includes("repair") || line.toLowerCase().includes("fix")) {
        return { type: "ai", content: line };
      }
      return { type: "info", content: line };
    });
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(output);
    toast({
      title: "Copied to clipboard",
      description: "Terminal output copied successfully",
    });
  };

  const logLines = output ? parseLogLines(output) : [];

  const getLineColor = (type: LogLine["type"]) => {
    switch (type) {
      case "success":
        return "text-success";
      case "error":
        return "text-destructive";
      case "warning":
        return "text-warning";
      case "ai":
        return "text-secondary";
      case "info":
      default:
        return "text-info";
    }
  };

  return (
    <div className="h-full flex flex-col bg-[hsl(var(--card))] dark:bg-gradient-to-br dark:from-[#11151c] dark:to-[#171b22] rounded-xl overflow-hidden border border-border shadow-[var(--shadow-premium)] dark:shadow-[var(--shadow-neon)]">
      {/* Premium gradient header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-card via-muted/30 to-card dark:from-[#171b22] dark:via-[#1a1f28] dark:to-[#171b22] border-b border-border/50">
        <div className="flex items-center gap-2.5">
          <div className="w-2 h-2 rounded-full bg-success animate-pulse-glow" />
          <TerminalIcon className="w-4 h-4 text-primary" />
          <span className="text-sm font-semibold">Terminal Output</span>
        </div>

        <div className="flex items-center gap-3">
          {responseTime && !isLoading && (
            <>
              {status === "success" && (
                <div className="flex items-center gap-1.5 text-xs px-2 py-1 rounded-md bg-success/10 text-success border border-success/20">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span className="font-medium">Success</span>
                </div>
              )}
              {status === "error" && (
                <div className="flex items-center gap-1.5 text-xs px-2 py-1 rounded-md bg-destructive/10 text-destructive border border-destructive/20">
                  <XCircle className="w-3.5 h-3.5" />
                  <span className="font-medium">Error</span>
                </div>
              )}
              <div className="flex items-center gap-1 text-xs text-muted-foreground px-2 py-1 rounded-md bg-muted/50">
                <Clock className="w-3.5 h-3.5" />
                <span>{responseTime}ms</span>
              </div>
            </>
          )}

          <div className="flex gap-1">
            {output && (
              <>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={handleCopy}
                  title="Copy output"
                >
                  <Copy className="w-3.5 h-3.5" />
                </Button>
                {onClear && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={onClear}
                    title="Clear output"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                )}
              </>
            )}
            {onRefresh && (
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={onRefresh}
                title="Refresh"
              >
                <RotateCw className="w-3.5 h-3.5" />
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Terminal body */}
      <div className="flex-1 p-4 overflow-auto font-mono text-sm dark:bg-[#0e1117]">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-full gap-6 scan-line">
            <AnimatedDoodle type={randomMsg.icon} className="scale-150" />
            <div className="text-center">
              <div className="text-2xl mb-2 animate-pulse-glow">{randomMsg.text.split(" ")[0]}</div>
              <div className="text-sm text-primary-glow">{randomMsg.text}</div>
            </div>
          </div>
        ) : output ? (
          <div className="space-y-0.5">
            {logLines.map((line, idx) => (
              <pre
                key={idx}
                className={`${getLineColor(line.type)} whitespace-pre-wrap leading-relaxed hover:bg-muted/5 px-2 py-0.5 rounded transition-colors`}
              >
                {line.content}
              </pre>
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-muted-foreground/50 text-center">
            <div>
              <TerminalIcon className="w-12 h-12 mx-auto mb-3 opacity-20" />
              <p className="text-sm">
                Click <span className="text-primary font-semibold">Run</span> to execute your code
                <br />
                or <span className="text-primary font-semibold">Repair</span> to fix any issues
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

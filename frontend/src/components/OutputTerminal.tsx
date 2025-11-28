import { CheckCircle2, XCircle, Clock } from "lucide-react";

interface OutputTerminalProps {
  output: string;
  status: "idle" | "success" | "error";
  responseTime?: number;
  isLoading?: boolean;
}

// Combined pool of all loading messages
const loadingMessages: string[] = [
  // hacker
  "💻 Breaching debugging firewall…",
  "🛰️ Routing your code through dark satellites…",
  "🔓 Cracking encrypted syntax layers…",
  "📡 Scanning for rogue semicolons…",
  "🧨 Injecting zero-day patches…",
  "🚁 Deploying tactical recursion drones…",
  "⚡ Overclocking computation units…",

  // dark humor
  "💀 Performing autopsy on your code corpse…",
  "🧨 Planting C4 on suspicious variables…",
  "🪦 Burying dead functions…",
  "🫠 Melting spaghetti code strands…",
  "🤡 Removing clown logic residue…",
  "😈 Creating emotional damage report…",

  // corporate
  "📈 Reporting your bugs to upper management…",
  "💼 Conducting code performance review… failed.",
  "📊 Monetizing runtime errors…",
  "📦 Packaging stack traces into deliverables…",
  "💸 Converting bugs into billable hours…",
  "🔒 Encrypting bad code and selling decryption key…",
];

export const OutputTerminal = ({
  output,
  status,
  responseTime,
  isLoading,
}: OutputTerminalProps) => {

  const randomMessage =
    loadingMessages[Math.floor(Math.random() * loadingMessages.length)];

  return (
    <div className="h-full flex flex-col bg-[hsl(220_25%_12%)] rounded-xl overflow-hidden border border-border/50">
      <div className="flex items-center justify-between px-4 py-2.5 bg-[hsl(220_25%_10%)] border-b border-border/30">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-success animate-pulse-glow" />
          <span className="text-xs font-medium text-muted-foreground">Terminal Output</span>
        </div>

        {responseTime && !isLoading && (
          <div className="flex items-center gap-3 text-xs">
            {status === "success" && (
              <div className="flex items-center gap-1.5 text-success">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Success</span>
              </div>
            )}

            {status === "error" && (
              <div className="flex items-center gap-1.5 text-destructive">
                <XCircle className="w-3.5 h-3.5" />
                <span>Error</span>
              </div>
            )}

            <div className="flex items-center gap-1 text-muted-foreground">
              <Clock className="w-3.5 h-3.5" />
              <span>{responseTime}ms</span>
            </div>
          </div>
        )}
      </div>

      <div className="flex-1 p-4 overflow-auto font-mono text-sm">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-primary-glow animate-fade-in">
            <div className="text-4xl animate-pulse-glow">
              {randomMessage.split(" ")[0]}
            </div>
            <div className="text-center text-sm">{randomMessage}</div>
          </div>
        ) : output ? (
          <pre className="text-foreground whitespace-pre-wrap">{output}</pre>
        ) : (
          <div className="flex items-center justify-center h-full text-muted-foreground/50 text-center">
            <p>
              Click "Run" to execute your code<br />or "Repair" to fix any issues
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

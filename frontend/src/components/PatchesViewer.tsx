import { Check, X, Code2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Patch {
  type: "add" | "remove" | "unchanged";
  line: number;
  content: string;
}

interface PatchesViewerProps {
  patches: Patch[];
  onApplyPatch: () => void;
  onRevertPatch: () => void;
}

export const PatchesViewer = ({ patches, onApplyPatch, onRevertPatch }: PatchesViewerProps) => {
  if (patches.length === 0) {
    return (
      <div className="h-full flex flex-col bg-card rounded-xl border border-border overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2.5 bg-muted/50 border-b border-border">
          <div className="flex items-center gap-2">
            <Code2 className="w-4 h-4 text-muted-foreground" />
            <span className="text-xs font-medium text-muted-foreground">Code Patches</span>
          </div>
        </div>
        <div className="flex-1 flex items-center justify-center text-muted-foreground/50 text-center p-4">
          <p>No patches yet.<br />Click "Repair" to see suggested fixes.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-card rounded-xl border border-border overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 bg-muted/50 border-b border-border">
        <div className="flex items-center gap-2">
          <Code2 className="w-4 h-4 text-muted-foreground" />
          <span className="text-xs font-medium text-muted-foreground">Code Patches</span>
        </div>
        <div className="flex gap-2">
          <Button onClick={onRevertPatch} variant="outline" size="sm" className="gap-1.5">
            <X className="w-3.5 h-3.5" />
            Revert
          </Button>
          <Button onClick={onApplyPatch} size="sm" className="gap-1.5 bg-gradient-to-r from-primary to-primary-glow">
            <Check className="w-3.5 h-3.5" />
            Apply
          </Button>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-4 font-mono text-xs">
        {patches.map((patch, index) => (
          <div
            key={index}
            className={`flex gap-3 py-1 px-2 rounded ${
              patch.type === "add"
                ? "bg-success/10 text-success"
                : patch.type === "remove"
                ? "bg-destructive/10 text-destructive"
                : "text-muted-foreground"
            }`}
          >
            <span className="text-muted-foreground/50 w-8 text-right flex-shrink-0">
              {patch.line}
            </span>
            <span className="w-4 flex-shrink-0">
              {patch.type === "add" ? "+" : patch.type === "remove" ? "-" : " "}
            </span>
            <span className="flex-1 whitespace-pre-wrap">{patch.content}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

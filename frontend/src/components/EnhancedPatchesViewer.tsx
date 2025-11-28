import { Check, X, Code2, GitCompare, LayoutList, List } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";

interface Patch {
  type: "add" | "remove" | "unchanged";
  line: number;
  content: string;
}

interface EnhancedPatchesViewerProps {
  patches: Patch[];
  onApplyPatch: () => void;
  onRevertPatch: () => void;
}

export const EnhancedPatchesViewer = ({
  patches,
  onApplyPatch,
  onRevertPatch,
}: EnhancedPatchesViewerProps) => {
  const [viewMode, setViewMode] = useState<"unified" | "split">("unified");

  if (patches.length === 0) {
    return (
      <div className="h-full flex flex-col bg-card dark:bg-gradient-to-br dark:from-[#11151c] dark:to-[#171b22] rounded-xl border border-border overflow-hidden shadow-[var(--shadow-premium)] dark:shadow-[var(--shadow-neon)]">
        <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-card via-muted/30 to-card dark:from-[#171b22] dark:via-[#1a1f28] dark:to-[#171b22] border-b border-border/50">
          <div className="flex items-center gap-2.5">
            <Code2 className="w-4 h-4 text-secondary" />
            <span className="text-sm font-semibold">Code Patches</span>
          </div>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground/50 text-center p-4">
          <GitCompare className="w-16 h-16 mb-4 opacity-20" />
          <p className="text-sm">
            No patches yet.
            <br />
            Click <span className="text-primary font-semibold">Repair</span> to see suggested fixes.
          </p>
        </div>
      </div>
    );
  }

  const addedCount = patches.filter((p) => p.type === "add").length;
  const removedCount = patches.filter((p) => p.type === "remove").length;
  const modifiedCount = patches.filter(
    (p, i, arr) =>
      p.type !== "unchanged" && i > 0 && arr[i - 1].type !== "unchanged"
  ).length;

  return (
    <div className="h-full flex flex-col bg-card dark:bg-gradient-to-br dark:from-[#11151c] dark:to-[#171b22] rounded-xl border border-border overflow-hidden shadow-[var(--shadow-premium)] dark:shadow-[var(--shadow-neon)]">
      {/* Premium gradient header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-card via-muted/30 to-card dark:from-[#171b22] dark:via-[#1a1f28] dark:to-[#171b22] border-b border-border/50">
        <div className="flex items-center gap-2.5">
          <GitCompare className="w-4 h-4 text-secondary" />
          <span className="text-sm font-semibold">Code Patches</span>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => setViewMode(viewMode === "unified" ? "split" : "unified")}
            variant="ghost"
            size="sm"
            className="gap-1.5 h-7 text-xs"
          >
            {viewMode === "unified" ? (
              <>
                <LayoutList className="w-3.5 h-3.5" />
                Split
              </>
            ) : (
              <>
                <List className="w-3.5 h-3.5" />
                Unified
              </>
            )}
          </Button>
          <Button onClick={onRevertPatch} variant="outline" size="sm" className="gap-1.5 h-7 text-xs">
            <X className="w-3.5 h-3.5" />
            Revert
          </Button>
          <Button
            onClick={onApplyPatch}
            size="sm"
            className="gap-1.5 h-7 text-xs bg-gradient-to-r from-primary to-primary-glow hover:shadow-lg hover:shadow-primary/20"
          >
            <Check className="w-3.5 h-3.5" />
            Apply
          </Button>
        </div>
      </div>

      {/* Summary bar */}
      <div className="px-4 py-2 bg-muted/30 border-b border-border/30 text-xs flex items-center gap-4">
        <span className="font-medium text-muted-foreground">🧩 Summary:</span>
        <span className="flex items-center gap-1.5 text-success">
          <span className="font-semibold">{addedCount}</span> added
        </span>
        <span className="flex items-center gap-1.5 text-destructive">
          <span className="font-semibold">{removedCount}</span> removed
        </span>
        {modifiedCount > 0 && (
          <span className="flex items-center gap-1.5 text-warning">
            <span className="font-semibold">{modifiedCount}</span> modified
          </span>
        )}
      </div>

      {/* Diff content */}
      <div className="flex-1 overflow-auto p-4 font-mono text-xs dark:bg-[#0e1117]">
        {viewMode === "unified" ? (
          <div className="space-y-0.5">
            {patches.map((patch, index) => (
              <div
                key={index}
                className={`flex gap-3 py-1.5 px-3 rounded-md transition-all ${
                  patch.type === "add"
                    ? "bg-success/10 dark:bg-success/5 text-success border-l-2 border-success"
                    : patch.type === "remove"
                    ? "bg-destructive/10 dark:bg-destructive/5 text-destructive border-l-2 border-destructive line-through"
                    : "text-muted-foreground hover:bg-muted/5"
                }`}
              >
                <span className="text-muted-foreground/50 w-10 text-right flex-shrink-0 select-none">
                  {patch.line}
                </span>
                <span className="w-6 flex-shrink-0 font-bold">
                  {patch.type === "add" ? "+" : patch.type === "remove" ? "-" : " "}
                </span>
                <span className="flex-1 whitespace-pre-wrap">{patch.content}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            {/* Before */}
            <div className="space-y-0.5">
              <div className="text-destructive font-semibold mb-2 text-sm">− Before</div>
              {patches
                .filter((p) => p.type !== "add")
                .map((patch, index) => (
                  <div
                    key={index}
                    className={`py-1.5 px-3 rounded-md ${
                      patch.type === "remove"
                        ? "bg-destructive/10 dark:bg-destructive/5 text-destructive"
                        : "text-muted-foreground"
                    }`}
                  >
                    <span className="text-muted-foreground/50 mr-3">{patch.line}</span>
                    <span>{patch.content}</span>
                  </div>
                ))}
            </div>

            {/* After */}
            <div className="space-y-0.5">
              <div className="text-success font-semibold mb-2 text-sm">+ After</div>
              {patches
                .filter((p) => p.type !== "remove")
                .map((patch, index) => (
                  <div
                    key={index}
                    className={`py-1.5 px-3 rounded-md ${
                      patch.type === "add"
                        ? "bg-success/10 dark:bg-success/5 text-success"
                        : "text-muted-foreground"
                    }`}
                  >
                    <span className="text-muted-foreground/50 mr-3">{patch.line}</span>
                    <span>{patch.content}</span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

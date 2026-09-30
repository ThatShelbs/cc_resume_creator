import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { FileWarning, Minus, Plus } from "lucide-react";
import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { Button } from "@/components/ui/button";
import { Tooltip } from "@/components/ui/overlays";
import { Skeleton } from "@/components/ui/primitives";
import { cn } from "@/lib/utils";

pdfjs.GlobalWorkerOptions.workerSrc = workerSrc;

function PaperSkeleton() {
  return (
    <div className="aspect-[8.5/11] w-full rounded-sm bg-white p-[8%] shadow-paper">
      <Skeleton className="mx-auto h-5 w-1/2 !bg-zinc-200" />
      <Skeleton className="mx-auto mt-3 h-2.5 w-2/3 !bg-zinc-100" />
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="mt-8 grid gap-2">
          <Skeleton className="h-3 w-1/4 !bg-zinc-200" />
          <Skeleton className="h-2.5 w-full !bg-zinc-100" />
          <Skeleton className="h-2.5 w-11/12 !bg-zinc-100" />
          <Skeleton className="h-2.5 w-4/5 !bg-zinc-100" />
        </div>
      ))}
    </div>
  );
}

/** The exact rendered PDF, drawn with pdf.js on a white "paper" sheet in both themes. */
export function PdfPreview({ url, className }: { url: string; className?: string }) {
  const wrap = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [pages, setPages] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(260, entry.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => setError(null), [url]);

  return (
    <div className={cn("relative", className)}>
      <div className="absolute right-2 top-2 z-10 flex items-center gap-1 rounded-lg border bg-background/90 p-0.5 shadow-soft backdrop-blur">
        <Tooltip content="Zoom out">
          <Button variant="ghost" size="icon-sm" className="size-7" onClick={() => setZoom((z) => Math.max(0.6, +(z - 0.15).toFixed(2)))} aria-label="Zoom out">
            <Minus />
          </Button>
        </Tooltip>
        <button type="button" onClick={() => setZoom(1)} className="w-11 text-center text-[11px] font-medium tabular-nums text-muted-foreground hover:text-foreground">
          {Math.round(zoom * 100)}%
        </button>
        <Tooltip content="Zoom in">
          <Button variant="ghost" size="icon-sm" className="size-7" onClick={() => setZoom((z) => Math.min(2, +(z + 0.15).toFixed(2)))} aria-label="Zoom in">
            <Plus />
          </Button>
        </Tooltip>
      </div>
      <div ref={wrap} className="w-full min-w-0 overflow-x-auto">
        {!width ? (
          <PaperSkeleton />
        ) : error ? (
          <div className="flex aspect-[8.5/11] w-full flex-col items-center justify-center gap-2 rounded-sm border border-dashed bg-background text-center text-sm text-muted-foreground">
            <FileWarning className="size-6" />
            Couldn't display the PDF.
            <span className="text-xs">{error}</span>
          </div>
        ) : (
          <Document
            key={url}
            file={url}
            loading={<PaperSkeleton />}
            onLoadSuccess={({ numPages }) => setPages(numPages)}
            onLoadError={(e) => setError(e.message)}
            className="grid justify-center gap-4"
          >
            {Array.from({ length: pages }, (_, i) => (
              <div key={i} className="relative">
                <Page
                  pageNumber={i + 1}
                  width={width * zoom}
                  className="overflow-hidden rounded-sm bg-white shadow-paper"
                  loading={<PaperSkeleton />}
                />
                {pages > 1 && (
                  <span className="absolute bottom-2 right-2 rounded bg-black/55 px-1.5 py-0.5 text-[10px] font-medium text-white">
                    {i + 1} / {pages}
                  </span>
                )}
              </div>
            ))}
          </Document>
        )}
      </div>
    </div>
  );
}

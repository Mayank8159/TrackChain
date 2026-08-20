// Consistent page title, breadcrumb, and actions.

import React from "react";
import Link from "next/link";
import { cn } from "../../lib/utils";

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface PageHeaderProps {
  title: string;
  description?: string;
  breadcrumbs?: BreadcrumbItem[];
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  description,
  breadcrumbs,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-scada-border pb-4 font-mono",
        className
      )}
    >
      <div className="space-y-1">
        {breadcrumbs && breadcrumbs.length > 0 && (
          <div className="flex items-center gap-1.5 text-[10px] text-scada-muted">
            <Link href="/" className="hover:text-scada-cyan transition-colors">
              HOME
            </Link>
            {breadcrumbs.map((b, i) => (
              <React.Fragment key={i}>
                <span>/</span>
                {b.href ? (
                  <Link href={b.href} className="hover:text-scada-cyan transition-colors">
                    {b.label.toUpperCase()}
                  </Link>
                ) : (
                  <span className="text-scada-text font-bold">{b.label.toUpperCase()}</span>
                )}
              </React.Fragment>
            ))}
          </div>
        )}
        <h1 className="text-lg font-bold uppercase tracking-wider text-scada-text">
          {title}
        </h1>
        {description && <p className="text-xs text-scada-muted">{description}</p>}
      </div>

      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  );
}

"use client"

import Link from "next/link"
import { ChevronRight, Home } from "lucide-react"
import { Fragment } from "react"

export interface BreadcrumbItem {
  label: string
  href?: string
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[]
  showHome?: boolean
}

export function Breadcrumbs({ items, showHome = true }: BreadcrumbsProps) {
  return (
    <nav className="flex items-center space-x-1 text-sm text-slate-400 mb-6" aria-label="Breadcrumb">
      {showHome && (
        <>
          <Link
            href="/"
            className="flex items-center hover:text-slate-200 transition-colors"
            aria-label="Accueil"
          >
            <Home className="h-4 w-4" />
          </Link>
          {items.length > 0 && <ChevronRight className="h-4 w-4 text-slate-600" />}
        </>
      )}

      {items.map((item, index) => {
        const isLast = index === items.length - 1

        return (
          <Fragment key={index}>
            {item.href && !isLast ? (
              <Link
                href={item.href}
                className="hover:text-slate-200 transition-colors"
              >
                {item.label}
              </Link>
            ) : (
              <span className={isLast ? "text-slate-200 font-medium" : ""}>
                {item.label}
              </span>
            )}

            {!isLast && <ChevronRight className="h-4 w-4 text-slate-600" />}
          </Fragment>
        )
      })}
    </nav>
  )
}

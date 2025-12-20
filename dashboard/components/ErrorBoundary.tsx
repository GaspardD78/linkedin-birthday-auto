'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error Boundary pour capturer les erreurs React et afficher un fallback UI.
 *
 * Utilisation:
 * ```tsx
 * <ErrorBoundary>
 *   <MonComposant />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    // Met à jour l&apos;état pour afficher le fallback UI au prochain render
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Logger l&apos;erreur

    // Appeler le callback onError si fourni
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
    });
  };

  render() {
    if (this.state.hasError) {
      // Si un fallback personnalisé est fourni, l&apos;utiliser
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Sinon, afficher le fallback par défaut
      return (
        <div className="flex min-h-[400px] flex-col items-center justify-center rounded-lg border border-red-200 bg-red-50 p-8 dark:border-red-800 dark:bg-red-950">
          <div className="flex flex-col items-center gap-4 text-center">
            <div className="rounded-full bg-red-100 p-3 dark:bg-red-900">
              <AlertTriangle className="h-8 w-8 text-red-600 dark:text-red-400" />
            </div>

            <div className="space-y-2">
              <h2 className="text-xl font-semibold text-red-900 dark:text-red-100">
                Une erreur est survenue
              </h2>
              <p className="max-w-md text-sm text-red-700 dark:text-red-300">
                {this.state.error?.message || "Une erreur inattendue s&apos;est produite"}
              </p>
            </div>

            <button
              onClick={this.handleReset}
              className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 dark:bg-red-700 dark:hover:bg-red-600"
            >
              <RefreshCw className="h-4 w-4" />
              Réessayer
            </button>

            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mt-4 w-full max-w-2xl text-left">
                <summary className="cursor-pointer text-sm font-medium text-red-700 dark:text-red-300">
                  Détails de l&apos;erreur (dev only)
                </summary>
                <pre className="mt-2 overflow-auto rounded-lg bg-red-100 p-4 text-xs text-red-900 dark:bg-red-900 dark:text-red-100">
                  {this.state.error.stack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

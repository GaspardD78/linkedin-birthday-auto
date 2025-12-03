'use client'

import React from 'react'
import { AlertTriangle, RefreshCw, Home } from 'lucide-react'
import { Button } from './ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'

interface Props {
  children: React.ReactNode
}

interface State {
  hasError: boolean
  error?: Error
  errorInfo?: React.ErrorInfo
}

/**
 * ErrorBoundary Component
 *
 * Catches React errors in any child component tree and displays a fallback UI
 * instead of crashing the entire application.
 *
 * Usage:
 * ```tsx
 * <ErrorBoundary>
 *   <YourComponent />
 * </ErrorBoundary>
 * ```
 */
export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error to console for debugging
    console.error('ErrorBoundary caught an error:', error, errorInfo)

    // You can also log the error to an error reporting service here
    // Example: logErrorToService(error, errorInfo)

    this.setState({ errorInfo })
  }

  handleReset = () => {
    // Reset error boundary state
    this.setState({ hasError: false, error: undefined, errorInfo: undefined })
  }

  handleGoHome = () => {
    // Navigate to home page
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-4">
          <Card className="max-w-2xl w-full border-red-500/20 bg-slate-900/50 backdrop-blur">
            <CardHeader>
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-full bg-red-500/20">
                  <AlertTriangle className="h-8 w-8 text-red-500" />
                </div>
                <div>
                  <CardTitle className="text-2xl text-white">Une erreur s'est produite</CardTitle>
                  <CardDescription className="text-slate-400 mt-1">
                    L'application a rencontré un problème inattendu
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Error Details */}
              {this.state.error && (
                <div className="bg-slate-950 border border-red-500/20 rounded-lg p-4">
                  <p className="text-sm font-semibold text-red-400 mb-2">Détails de l'erreur :</p>
                  <code className="text-xs text-slate-300 font-mono block overflow-x-auto">
                    {this.state.error.message}
                  </code>

                  {/* Stack trace (only in development) */}
                  {process.env.NODE_ENV === 'development' && this.state.error.stack && (
                    <details className="mt-3">
                      <summary className="text-xs text-slate-400 cursor-pointer hover:text-slate-300">
                        Stack Trace (dev only)
                      </summary>
                      <pre className="text-xs text-slate-400 mt-2 overflow-x-auto max-h-64">
                        {this.state.error.stack}
                      </pre>
                    </details>
                  )}
                </div>
              )}

              {/* Component Stack (development only) */}
              {process.env.NODE_ENV === 'development' && this.state.errorInfo?.componentStack && (
                <details className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                  <summary className="text-xs text-slate-400 cursor-pointer hover:text-slate-300">
                    Component Stack (dev only)
                  </summary>
                  <pre className="text-xs text-slate-400 mt-2 overflow-x-auto max-h-64">
                    {this.state.errorInfo.componentStack}
                  </pre>
                </details>
              )}

              {/* Actions */}
              <div className="flex flex-col sm:flex-row gap-3 pt-4">
                <Button
                  onClick={this.handleReset}
                  className="flex-1 gap-2"
                  variant="default"
                >
                  <RefreshCw className="h-4 w-4" />
                  Réessayer
                </Button>
                <Button
                  onClick={this.handleGoHome}
                  variant="outline"
                  className="flex-1 gap-2"
                >
                  <Home className="h-4 w-4" />
                  Retour à l'accueil
                </Button>
              </div>

              {/* Help Text */}
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
                <p className="text-sm text-blue-400">
                  <strong>Que faire ?</strong>
                </p>
                <ul className="text-xs text-slate-400 mt-2 space-y-1 list-disc list-inside">
                  <li>Cliquez sur "Réessayer" pour tenter de résoudre le problème</li>
                  <li>Si l'erreur persiste, rechargez la page (F5)</li>
                  <li>En dernier recours, retournez à l'accueil</li>
                  {process.env.NODE_ENV === 'development' && (
                    <li>En mode développement, vérifiez la console pour plus de détails</li>
                  )}
                </ul>
              </div>
            </CardContent>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}

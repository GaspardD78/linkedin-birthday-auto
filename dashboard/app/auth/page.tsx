"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useDropzone } from "react-dropzone"
import { uploadAuthState } from "@/lib/api"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { CheckCircle2, UploadCloud, FileJson, AlertTriangle, ExternalLink, ArrowLeft } from "lucide-react"
import { useToast } from "@/components/ui/use-toast"
import Link from "next/link"
import { Button } from "@/components/ui/button"

export default function AuthPage() {
  const router = useRouter()
  const [uploading, setUploading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { toast } = useToast()

  const onDrop = async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    if (file.name !== "auth_state.json") {
      setError("Le fichier doit se nommer exactement 'auth_state.json'")
      return
    }

    setUploading(true)
    setError(null)
    setSuccess(false)

    try {
      await uploadAuthState(file)
      setSuccess(true)
      toast({
        title: "Authentification réussie",
        description: "Votre session a été mise à jour avec succès.",
      })
      setTimeout(() => router.push("/"), 1500)
    } catch (err: any) {
      setError(err.message || "Erreur lors de l'upload")
      toast({
        variant: "destructive",
        title: "Erreur",
        description: err.message || "L'upload a échoué",
      })
    } finally {
      setUploading(false)
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/json': ['.json']
    },
    maxFiles: 1
  })

  return (
    <div className="container mx-auto max-w-2xl py-12 px-4">
      <div className="mb-8">
        <Link href="/">
          <Button variant="ghost" className="mb-4 pl-0 hover:bg-transparent hover:text-primary">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Retour au Dashboard
          </Button>
        </Link>
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight mb-2">Connexion LinkedIn</h1>
          <p className="text-muted-foreground">
            Importez votre session active pour permettre au bot d&apos;agir en votre nom.
          </p>
        </div>
      </div>

      <Card className="border-2 border-dashed border-muted-foreground/25 shadow-lg bg-card/50 backdrop-blur">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UploadCloud className="h-6 w-6 text-primary" />
            Upload de Session
          </CardTitle>
          <CardDescription>
            Glissez-déposez votre fichier <code>auth_state.json</code> ici.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            {...getRootProps()}
            className={`
              flex flex-col items-center justify-center p-10 border-2 border-dashed rounded-xl transition-all cursor-pointer
              ${isDragActive ? "border-primary bg-primary/10" : "border-muted-foreground/20 hover:border-primary/50 hover:bg-muted/50"}
              ${success ? "border-green-500 bg-green-500/10" : ""}
            `}
          >
            <input {...getInputProps()} />

            {success ? (
              <div className="text-center animate-in zoom-in duration-300">
                <CheckCircle2 className="h-16 w-16 text-green-500 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-green-500">Session Validée !</h3>
                <p className="text-muted-foreground mt-2">Redirection en cours...</p>
              </div>
            ) : (
              <div className="text-center space-y-4">
                <div className="bg-background p-4 rounded-full inline-block shadow-sm">
                  <FileJson className="h-10 w-10 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-lg font-medium">
                    {isDragActive ? "Lâchez le fichier ici..." : "Glissez auth_state.json ici"}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    ou cliquez pour parcourir vos fichiers
                  </p>
                </div>
              </div>
            )}
          </div>

          {error && (
            <Alert variant="destructive" className="mt-6">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Erreur</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="mt-8 bg-muted/30 p-4 rounded-lg border text-sm space-y-3">
            <h4 className="font-semibold flex items-center gap-2">
              <ExternalLink className="h-4 w-4" />
              Comment obtenir ce fichier ?
            </h4>
            <ol className="list-decimal list-inside space-y-2 text-muted-foreground">
              <li>Installez l&apos;extension Chrome <strong>EditThisCookie</strong>.</li>
              <li>Connectez-vous à <strong>LinkedIn.com</strong> sur votre navigateur.</li>
              <li>Ouvrez l&apos;extension et cliquez sur l&apos;icône <strong>Exporter</strong> (flèche vers l&apos;extérieur).</li>
              <li>Collez le contenu dans un nouveau fichier nommé <code>auth_state.json</code>.</li>
              <li>Uploadez ce fichier ci-dessus.</li>
            </ol>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

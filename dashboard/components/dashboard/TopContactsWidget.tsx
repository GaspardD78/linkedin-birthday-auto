"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Users } from "lucide-react"
import { useState, useEffect } from "react"

interface Contact {
  id: number
  name: string
  profile_url: string
  message_count: number
}

export function TopContactsWidget() {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchTopContacts = async () => {
      try {
        const res = await fetch('/api/contacts?limit=5&sort=messages', { cache: 'no-store' })
        if (res.ok) {
          const data = await res.json()
          setContacts(data.contacts?.slice(0, 5) || [])
        }
      } catch (e) {
      } finally {
        setLoading(false)
      }
    }

    fetchTopContacts()

    // Refresh every 5 minutes
    const interval = setInterval(fetchTopContacts, 300000)
    return () => clearInterval(interval)
  }, [])

  // Generate initials from name
  const getInitials = (name: string) => {
    const parts = name.trim().split(' ')
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
    }
    return name.substring(0, 2).toUpperCase()
  }

  // Generate a color based on name
  const getAvatarColor = (name: string) => {
    const colors = [
      'bg-purple-500',
      'bg-blue-500',
      'bg-green-500',
      'bg-yellow-500',
      'bg-pink-500',
      'bg-indigo-500',
      'bg-teal-500',
      'bg-orange-500'
    ]
    const index = name.length % colors.length
    return colors[index]
  }

  if (loading) {
    return (
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <div className="h-5 bg-slate-700 rounded w-1/2"></div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={`skeleton-${i}`} className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-slate-700"></div>
                <div className="flex-1">
                  <div className="h-4 bg-slate-700 rounded w-3/4 mb-1"></div>
                  <div className="h-3 bg-slate-700 rounded w-1/2"></div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-medium text-slate-200 flex items-center gap-2">
          <Users className="h-5 w-5" />
          Top 5 Contacts
        </CardTitle>
      </CardHeader>
      <CardContent>
        {contacts.length === 0 ? (
          <div className="text-center py-6 text-slate-500 text-sm">
            Aucun contact disponible
          </div>
        ) : (
          <div className="space-y-3">
            {contacts.map((contact) => (
              <div
                key={contact.id}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-800/50 transition-colors"
              >
                {/* Avatar with initials */}
                <div
                  className={`h-10 w-10 rounded-full ${getAvatarColor(contact.name)} flex items-center justify-center font-semibold text-white text-sm flex-shrink-0`}
                >
                  {getInitials(contact.name)}
                </div>

                {/* Contact info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-200 truncate">
                    {contact.name}
                  </p>
                  <p className="text-xs text-slate-500">
                    {contact.message_count || 0} message{(contact.message_count || 0) > 1 ? 's' : ''}
                  </p>
                </div>

                {/* Message count badge */}
                <Badge
                  variant="outline"
                  className="bg-slate-800 text-slate-300 border-slate-700"
                >
                  {contact.message_count || 0}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

import { useState } from 'react';

interface CustomerInfo {
  name: string;
  email: string;
  phone: string;
  address: string;
  customer_since: string;
}

interface PolicyInfo {
  policy_number: string;
  policy_type: string;
  premium_monthly: number;
  payment_status: string;
  coverage: {
    buildings?: number;
    contents?: number;
    personal_liability?: number;
    alternative_accommodation?: number;
    accidental_damage?: boolean;
    legal_expenses?: boolean;
  };
  excess: {
    standard?: number;
    escape_of_water?: number;
    subsidence?: number;
  };
}

interface Claim {
  claim_id: string;
  date: string;
  type: string;
  description: string;
  status: string;
  amount_claimed: number;
  amount_paid: number;
  notes?: string;
}

interface Ticket {
  ticket_id: string;
  date: string;
  subject: string;
  summary: string;
  status: string;
  resolution: string;
  agent: string;
}

interface CustomerNote {
  date: string;
  note: string;
  added_by: string;
}

interface ConversationMessage {
  role: 'customer' | 'ai_assistant';
  content: string;
}

interface HandoffData {
  conversation_summary: string;
  conversation_log: ConversationMessage[];
  customer_history: {
    customer_info: CustomerInfo;
    policy: PolicyInfo;
    previous_claims: Claim[];
    previous_tickets: Ticket[];
    customer_notes: CustomerNote[];
    risk_score: string;
    no_claims_bonus: {
      years: number;
      protected: boolean;
    };
  };
  handoff_timestamp: string;
  handoff_reason: string;
}

interface AgentViewProps {
  handoffData: HandoffData | null;
  onClose: () => void;
}

export default function AgentView({ handoffData, onClose }: AgentViewProps) {
  const [activeTab, setActiveTab] = useState<'summary' | 'conversation' | 'history' | 'claims'>('summary');

  if (!handoffData) {
    return (
      <div className="fixed inset-0 bg-gray-900 flex items-center justify-center">
        <div className="text-white text-center">
          <div className="animate-spin w-12 h-12 border-4 border-white/20 border-t-white rounded-full mx-auto mb-4" />
          <p>Loading agent view...</p>
        </div>
      </div>
    );
  }

  const { conversation_summary, conversation_log, customer_history, handoff_timestamp, handoff_reason } = handoffData;
  const { customer_info, policy, previous_claims, previous_tickets, customer_notes, risk_score, no_claims_bonus } = customer_history;

  return (
    <div className="fixed inset-0 bg-gray-900 text-white overflow-hidden flex flex-col">
      {/* Header */}
      <header className="bg-gradient-to-r from-purple-900 to-indigo-900 px-6 py-4 flex items-center justify-between shadow-lg">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-semibold">Agent Dashboard</h1>
            <p className="text-sm text-purple-200">Customer Handoff</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="text-right text-sm">
            <p className="text-purple-200">Handoff Time</p>
            <p className="font-medium">{new Date(handoff_timestamp).toLocaleString()}</p>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </header>

      {/* Customer Quick Info Bar */}
      <div className="bg-gray-800 px-6 py-3 flex items-center justify-between border-b border-gray-700">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-sm">Customer:</span>
            <span className="font-semibold">{customer_info.name}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-sm">Policy:</span>
            <span className="font-mono text-sm">{policy.policy_number}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-sm">Status:</span>
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
              policy.payment_status === 'current' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
            }`}>
              {policy.payment_status}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-sm">Risk:</span>
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
              risk_score === 'low' ? 'bg-green-500/20 text-green-400' : 
              risk_score === 'medium' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'
            }`}>
              {risk_score}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-gray-400">{customer_info.phone}</span>
          <span className="text-gray-400">|</span>
          <span className="text-gray-400">{customer_info.email}</span>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="bg-gray-800/50 px-6 py-2 flex gap-2 border-b border-gray-700">
        {(['summary', 'conversation', 'history', 'claims'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === tab
                ? 'bg-purple-600 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-700'
            }`}
          >
            {tab === 'summary' && '📋 Summary'}
            {tab === 'conversation' && '💬 Conversation'}
            {tab === 'history' && '📁 Ticket History'}
            {tab === 'claims' && '📄 Claims'}
          </button>
        ))}
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Summary Tab */}
        {activeTab === 'summary' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Conversation Summary Card */}
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
                  <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </span>
                Conversation Summary
              </h2>
              <div className="prose prose-invert prose-sm max-w-none">
                <div className="bg-gray-900/50 rounded-lg p-4 text-gray-300 whitespace-pre-wrap leading-relaxed">
                  {conversation_summary}
                </div>
              </div>
              <div className="mt-4 pt-4 border-t border-gray-700">
                <p className="text-sm text-gray-400">
                  <strong>Handoff Reason:</strong> {handoff_reason}
                </p>
              </div>
            </div>

            {/* Customer Profile Card */}
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                  <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </span>
                Customer Profile
              </h2>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wider">Name</p>
                    <p className="font-medium">{customer_info.name}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wider">Customer Since</p>
                    <p className="font-medium">{new Date(customer_info.customer_since).toLocaleDateString()}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wider">Email</p>
                    <p className="font-medium text-sm">{customer_info.email}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wider">Phone</p>
                    <p className="font-medium">{customer_info.phone}</p>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wider">Address</p>
                  <p className="font-medium text-sm">{customer_info.address}</p>
                </div>
              </div>
            </div>

            {/* Policy Details Card */}
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span className="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center">
                  <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </span>
                Policy Details
              </h2>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wider">Policy Number</p>
                    <p className="font-mono font-medium">{policy.policy_number}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wider">Type</p>
                    <p className="font-medium">{policy.policy_type}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wider">Monthly Premium</p>
                    <p className="font-medium text-green-400">£{policy.premium_monthly}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-400 uppercase tracking-wider">No Claims Bonus</p>
                    <p className="font-medium">
                      {no_claims_bonus.years} years {no_claims_bonus.protected && <span className="text-xs text-green-400">(Protected)</span>}
                    </p>
                  </div>
                </div>
                
                <div className="pt-3 border-t border-gray-700">
                  <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">Coverage Limits</p>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Buildings:</span>
                      <span>£{policy.coverage.buildings?.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Contents:</span>
                      <span>£{policy.coverage.contents?.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Personal Liability:</span>
                      <span>£{policy.coverage.personal_liability?.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Alt. Accommodation:</span>
                      <span>£{policy.coverage.alternative_accommodation?.toLocaleString()}</span>
                    </div>
                  </div>
                </div>

                <div className="pt-3 border-t border-gray-700">
                  <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">Excess</p>
                  <div className="flex gap-4 text-sm">
                    <div>
                      <span className="text-gray-400">Standard:</span>
                      <span className="ml-1">£{policy.excess.standard}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Water:</span>
                      <span className="ml-1">£{policy.excess.escape_of_water}</span>
                    </div>
                    <div>
                      <span className="text-gray-400">Subsidence:</span>
                      <span className="ml-1">£{policy.excess.subsidence}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Stats Card */}
            <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <span className="w-8 h-8 rounded-lg bg-yellow-500/20 flex items-center justify-center">
                  <svg className="w-5 h-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </span>
                Customer Stats
              </h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-900/50 rounded-lg p-4 text-center">
                  <p className="text-3xl font-bold text-blue-400">{previous_claims.length}</p>
                  <p className="text-sm text-gray-400">Previous Claims</p>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-4 text-center">
                  <p className="text-3xl font-bold text-purple-400">{previous_tickets.length}</p>
                  <p className="text-sm text-gray-400">Support Tickets</p>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-4 text-center">
                  <p className="text-3xl font-bold text-green-400">{conversation_log.length}</p>
                  <p className="text-sm text-gray-400">Messages in Session</p>
                </div>
                <div className="bg-gray-900/50 rounded-lg p-4 text-center">
                  <p className="text-3xl font-bold text-yellow-400">{customer_notes.length}</p>
                  <p className="text-sm text-gray-400">Agent Notes</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Conversation Tab */}
        {activeTab === 'conversation' && (
          <div className="max-w-3xl mx-auto">
            <div className="bg-gray-800 rounded-xl border border-gray-700">
              <div className="px-6 py-4 border-b border-gray-700">
                <h2 className="text-lg font-semibold">Full Conversation Log</h2>
                <p className="text-sm text-gray-400">{conversation_log.length} messages</p>
              </div>
              <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
                {conversation_log.map((msg, idx) => (
                  <div
                    key={idx}
                    className={`flex ${msg.role === 'customer' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] px-4 py-3 rounded-2xl ${
                        msg.role === 'customer'
                          ? 'bg-blue-600 text-white rounded-br-sm'
                          : 'bg-gray-700 text-gray-100 rounded-bl-sm'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1 text-xs opacity-70">
                        {msg.role === 'customer' ? '👤 Customer' : '🤖 AI Assistant'}
                      </div>
                      <p className="text-sm leading-relaxed">{msg.content}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold">Previous Support Tickets</h2>
            {previous_tickets.length === 0 ? (
              <div className="bg-gray-800 rounded-xl p-8 text-center text-gray-400">
                No previous support tickets found.
              </div>
            ) : (
              <div className="grid gap-4">
                {previous_tickets.map((ticket) => (
                  <div key={ticket.ticket_id} className="bg-gray-800 rounded-xl p-5 border border-gray-700">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-sm text-gray-400">{ticket.ticket_id}</span>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            ticket.status === 'resolved' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
                          }`}>
                            {ticket.status}
                          </span>
                        </div>
                        <h3 className="font-semibold mt-1">{ticket.subject}</h3>
                      </div>
                      <div className="text-right text-sm">
                        <p className="text-gray-400">{new Date(ticket.date).toLocaleDateString()}</p>
                        <p className="text-gray-500">Agent: {ticket.agent}</p>
                      </div>
                    </div>
                    <p className="text-gray-300 text-sm mb-2">{ticket.summary}</p>
                    <p className="text-sm">
                      <span className="text-gray-400">Resolution:</span>{' '}
                      <span className="text-gray-200">{ticket.resolution}</span>
                    </p>
                  </div>
                ))}
              </div>
            )}

            {customer_notes.length > 0 && (
              <>
                <h2 className="text-xl font-semibold mt-8">Agent Notes</h2>
                <div className="grid gap-3">
                  {customer_notes.map((note, idx) => (
                    <div key={idx} className="bg-gray-800 rounded-xl p-4 border border-gray-700">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-gray-400">{new Date(note.date).toLocaleDateString()}</span>
                        <span className="text-sm text-gray-500">— {note.added_by}</span>
                      </div>
                      <p className="text-gray-200">{note.note}</p>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {/* Claims Tab */}
        {activeTab === 'claims' && (
          <div className="space-y-6">
            <h2 className="text-xl font-semibold">Previous Claims</h2>
            {previous_claims.length === 0 ? (
              <div className="bg-gray-800 rounded-xl p-8 text-center text-gray-400">
                No previous claims found. This is the customer's first claim.
              </div>
            ) : (
              <div className="grid gap-4">
                {previous_claims.map((claim) => (
                  <div key={claim.claim_id} className="bg-gray-800 rounded-xl p-5 border border-gray-700">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-sm text-gray-400">{claim.claim_id}</span>
                          <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded-lg text-sm font-medium">
                            {claim.type}
                          </span>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            claim.status === 'settled' ? 'bg-green-500/20 text-green-400' : 
                            claim.status === 'pending' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-gray-500/20 text-gray-400'
                          }`}>
                            {claim.status}
                          </span>
                        </div>
                      </div>
                      <div className="text-right text-sm text-gray-400">
                        {new Date(claim.date).toLocaleDateString()}
                      </div>
                    </div>
                    <p className="text-gray-300 mb-4">{claim.description}</p>
                    <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-700">
                      <div>
                        <p className="text-xs text-gray-400 uppercase">Claimed</p>
                        <p className="font-semibold text-lg">£{claim.amount_claimed.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400 uppercase">Paid</p>
                        <p className="font-semibold text-lg text-green-400">£{claim.amount_paid.toLocaleString()}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400 uppercase">Difference</p>
                        <p className="font-semibold text-lg text-yellow-400">
                          £{(claim.amount_claimed - claim.amount_paid).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    {claim.notes && (
                      <div className="mt-4 pt-3 border-t border-gray-700">
                        <p className="text-sm text-gray-400">
                          <span className="font-medium">Notes:</span> {claim.notes}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <footer className="bg-gray-800 border-t border-gray-700 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg font-medium transition-colors flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            </svg>
            Call Customer
          </button>
          <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-colors flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            Send Email
          </button>
        </div>
        <div className="flex items-center gap-3">
          <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg font-medium transition-colors">
            Create New Ticket
          </button>
          <button className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 rounded-lg font-medium transition-colors">
            Start Claim Process
          </button>
        </div>
      </footer>
    </div>
  );
}

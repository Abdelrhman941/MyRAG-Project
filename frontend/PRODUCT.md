# RAG Document-Chat: Frontend Product Definition

## 1. Product Overview
A premium, minimal, professional RAG (Retrieval-Augmented Generation) document-chat application. The product allows a single user to upload documents, track their ingestion, and ask questions across their knowledge base inside isolated chat sessions. It prioritizes clarity, focus, and utility over generic dashboard visual noise.

## 2. Product Goals
- Deliver a focused, calm, and highly readable user experience.
- Provide a robust interface for chatting with documents with immediate, clear source attribution.
- Offer transparent upload and processing states.
- Ensure cross-session independence visually.
- Avoid unnecessary "AI product" UI bloat (e.g., tools, marketplaces, complex nav bars).

## 3. Target MVP Experience
1. Upload documents and monitor their background ingestion status.
2. Ask questions about the ingested knowledge.
3. Receive text answers with explicit source citations.
4. Continue the conversation contextually within independent chat sessions.

## 4. Information Architecture
The application shell is divided into two primary structural areas:

**Sidebar** (Navigation & History)
- New Chat (Primary Action)
- Chat Sessions (List of previous conversations)
- Documents (List of uploaded knowledge)

**Main Content Area** (Action & Consumption)
- Chat history for the selected session
- Interactive prompt composer
- Document management (when viewing documents)

## 5. Screen/Component Model
- **App Shell**: Persistent sidebar with collapsible behavior on small screens.
- **Chat View**: The default and primary surface. Displays a scrollable conversation log, loading indicators for generation, error states, and a fixed prompt composer at the bottom.
- **Document View**: A list or clean table layout displaying uploaded documents, their statuses (`uploaded`, `processing`, `ready`, `failed`), and minimal actions (Delete).
- **Prompt Composer**: A clean text input area with an explicit send action, supporting "Enter to send". Styled taking inspiration from the 21st.dev ChatGPT-style prompt input.

## 6. UX Flows
1. **First visit**: Brief branded splash, leading directly into a new empty chat session.
2. **Create session**: "New Chat" clears the main area and prepares a fresh session context.
3. **Upload documents**: User selects multiple files (up to 10). UI shows immediate local placeholder rows with an "uploading/processing" indicator.
4. **Processing → ready/failed**: UI polls or refreshes to transition document states. Duplicates or oversize files trigger friendly, specific error messages.
5. **Ask a question**: Prompt composer locks/disables, loading skeleton/spinner appears in the chat log.
6. **Receive answer + sources**: The assistant message renders markdown text, followed by subtle source citation pills/links.
7. **Follow-up question**: Extends the current conversation log.
8. **Switch session**: Clicking a sidebar session instantly swaps the chat history in the main area.
9. **Delete document**: UI confirms (or deletes immediately if low-risk), removes the document from the list, and prevents its future citations.
10. **Refresh/reload application**: Data is re-fetched, showing skeleton loaders in place of content until ready.

## 7. Session & Document Relationship
**REQUIRED PRODUCT INVARIANT**: Documents are strictly scoped to a single chat session.
- Documents uploaded while in a specific session belong exclusively to that session.
- Switching to a different session visually filters the document list to show only that session's documents.
- Queries within a session strictly and exclusively query that session's documents.
- This is not optional behavior; the UI must never present a "global" document list.

## 8. Loading/Skeleton Strategy
- **First Visit / Initial App Load**: A brief, minimal, premium branded splash state. No full-screen animated extravaganzas.
- **Subsequent Refresh / Navigation Loads**:
  - Use exact-dimension skeleton UI elements instead of generic spinners.
  - Skeletons must preserve the final layout to prevent Cumulative Layout Shift (CLS).
  - Explicit skeleton designs required for: Sidebar session lists, Document lists, Chat message blocks, and Document rows.

## 9. Chat Experience
- Modeled after familiar, modern AI chat products (e.g., ChatGPT, Claude).
- Clean conversation area with distinct user and assistant message styling.
- Clear generating states.
- The Prompt Composer remains locked to the bottom, handling disabled states naturally during generation or when empty.
- Document uploads are a distinct management action, not an arbitrary "attachment" inside the chat input.

## 10. Document Experience
- **Multi-file Upload**: Support for selecting multiple files at once.
- **Status Visibility**: Clear visual distinction between `uploaded` (waiting), `processing` (active), `ready` (success), and `failed` (error).
- **Error Handling**: Rate limits (429) show "You're uploading too fast — try again later". Deduplication conflicts (409) show a friendly "Document already exists" notice.
- **Actions**: Simple delete action per document. Refresh/update capability to track background ingestion.

## 11. Source Citation Experience
- Citations must display the document name and chunk reference.
- Presentation must be readable but unobtrusive (e.g., small footnote pills or inline reference numbers).
- Expanding citations to view raw chunk text is deferred unless explicitly supported by the backend contract.

## 12. Responsive Behavior
- **Desktop**: Persistent side-by-side layout (Sidebar + Main Content).
- **Tablet**: Sidebar remains accessible but may adopt a drawer/overlay pattern depending on orientation.
- **Mobile**: Sidebar fully collapses behind a hamburger menu. The Chat composer adjusts to avoid keyboard occlusion and remains highly usable.

## 13. Accessibility
- **Keyboard Navigation**: Full support for traversing sessions, documents, and chat.
- **Focus States**: Explicit, high-contrast focus rings for all interactive elements.
- **Semantics**: Strict use of semantic HTML (`<button>`, `<nav>`, `<main>`).
- **Screen Readers**: `aria-labels` on all icon-only buttons (e.g., send button, delete button).
- **Reduced Motion**: Respect `prefers-reduced-motion` for any UI transitions.

## 14. Design System Rules
- **Foundation**: `shadcn/ui` is the absolute primary foundation.
- **Augmentation**: `21st.dev` blocks are used selectively and exclusively for high-value components (e.g., the prompt composer or message styling).
- **Consistency**: Do not mix disparate visual patterns. Maintain strict consistency in typography, spacing, border radii, and interaction states.
- **No Component Shopping**: Use what is available in the established stack; do not import external libraries without explicit justification.

## 15. Performance Principles
- **Client Requests**: Minimize redundant data fetching.
- **Caching**: Reuse server data across navigations where appropriate.
- **Optimistic UI**: Use optimistic updates cautiously, only where backend correctness guarantees it (e.g., deleting a document).
- **Feedback**: Immediate visual feedback for all user actions.
- **State Management**: Rely on native React and Next.js capabilities. Do not introduce global state libraries (Zustand, Redux) unless absolutely mandated by architectural complexity.

## 16. Current Backend Constraints
**CRITICAL ARCHITECTURE NOTE:**
The current backend retrieval contract (`POST /api/v1/chat/sessions/{session_id}/messages` and the Qdrant adapter) searches **all** `ready` documents globally. It does not currently scope retrieval by `session_id`.

**BLOCKING GAP:**
Stage 08 frontend implementation is explicitly **PAUSED**. The UI cannot and will not be built with a misleading global-document UX. The backend contract (database, APIs, and Qdrant filtering) must be refactored to support strict session-scoping before frontend development proceeds.

## 17. Future/Deferred Capabilities
- Streaming responses (SSE/WebSockets).
- Semantic long-term memory.
- Advanced document parsing/management features.
- Authentication and multi-user boundaries.
- Re-ranking of search results.

## 18. Explicit Non-Goals
- Complex dashboard features (billing, teams, settings).
- "Agent Marketplace" or plugin UI.
- Direct filesystem manipulation outside of the provided API.
- Implementing UI for backend routes that do not yet exist.

import type { components } from './schema'

type Schema<Name extends keyof components['schemas']> = components['schemas'][Name]

export type Collection = Schema<'CollectionOut'>
export type ReadingSummary = Schema<'ReadingSummary'>
export type ReadingDetail = Schema<'ReadingDetail'>
export type ReadingContext = Schema<'ReadingContext'>
export type ContextCast = Schema<'ContextCast'>
export type ContextDrawResult = Schema<'ContextDrawResult'>
export type ContextSource = Schema<'ContextSource'>
export type ContextTradition = Schema<'ContextTradition'>
export type ContextInterpretation = Schema<'ContextInterpretation'>
export type ContextCorrespondence = Schema<'ContextCorrespondence'>
export type IChingOut = Schema<'IChingOut'>
export type IChingText = Schema<'IChingTextContext'>
export type Hexagram = Schema<'HexagramContext'>
export type Note = Schema<'NoteOut'>
export type Spread = Schema<'SpreadOut'>
export type SpreadCreate = Schema<'SpreadCreate'>
export type SpreadPatch = Schema<'SpreadPatch'>
export type Cast = Schema<'CastOut'>
export type CorpusStatus = Schema<'CorpusStatus'>
export type ReadingCreate = Schema<'ReadingCreate'>
export type DrawRequest = Schema<'DrawRequest'>
export type IChingCastRequest = Schema<'IChingCastRequest'>
export type NoteCreate = Schema<'NoteCreate'>

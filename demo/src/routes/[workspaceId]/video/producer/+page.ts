export const load = ({ params, url }: { params: { workspaceId: string }, url: URL }) => {
	const workspaceId = params.workspaceId;
	const roomId = url.searchParams.get('room') || '';
	return {
		workspaceId: workspaceId,
		roomId: roomId
	};
}; 
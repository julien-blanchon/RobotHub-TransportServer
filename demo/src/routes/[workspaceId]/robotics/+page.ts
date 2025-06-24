export const load = ({ params }: { params: { workspaceId: string } }) => {
	const workspaceId = params.workspaceId;
	return {
		workspaceId: workspaceId
	};
}; 
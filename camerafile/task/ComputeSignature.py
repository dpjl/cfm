class ComputeSignature:

    @staticmethod
    def execute(signature_metadata):
        try:
            signature_metadata.compute_value()
            return signature_metadata
        except:
            print("Error during compute_signature_task execution for " + str(signature_metadata.media_path))
            return signature_metadata
